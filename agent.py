from typing import Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_ollama import OllamaLLM
from sentence_transformers import SentenceTransformer
from config import CLASSIFY_INTENT_PROMPT, PROMPT_FOR_QA, EMBEDDINGS_MODEL, PROMPT_FOR_SUMMARY, PROMPT_FOR_MERGING_SUMMARIES
from services.text_utils import hybrid_search, chunk_text
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    user_input: str
    retrieved_docs: Optional[list]
    response: Optional[str]
    doc_id: Optional[str]
    new_title: Optional[str]
    new_content: Optional[str]
    intent: Optional[str]
    summaries: Optional[str]
    summarized_docs: Optional[str]



class Agent:
    def __init__(self, es, index_name, llm_model):
        """Initialize the agent with Elasticsearch and LangChain models."""
        self.es = es
        self.index_name = index_name
        self.llm = OllamaLLM(model=llm_model, temperature=0.0)
        self.embeddings = SentenceTransformer(EMBEDDINGS_MODEL, device="cuda")
        
        self.workflow = self._build_workflow(

        )

    def _build_workflow(self):
        workflow = StateGraph(AgentState)

        # Add nodes (same as before)
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("add_document", self.add_document)
        workflow.add_node("remove_document", self.remove_document)
        workflow.add_node("search_document", self.search_document)
        workflow.add_node("update_document", self.update_document)
        workflow.add_node("summarize_documents", self.summarize_documents)
        workflow.add_node("merge_summaries", self.merge_summaries)
        workflow.add_node("answer_question", self.answer_question)

        # Conditional edges from classify_intent
        workflow.add_conditional_edges(
            "classify_intent",
            lambda state: state["intent"],
            {
                "add_document": "add_document",
                "remove_document": "remove_document",
                "search_document": "search_document",
                "update_document": "update_document",
                "answer_question": "search_document",
            }
        )

        # Linear flow for question answering
        workflow.add_edge("search_document", "summarize_documents")
        workflow.add_edge("summarize_documents", "merge_summaries")
        workflow.add_edge("merge_summaries", "answer_question")
        workflow.add_edge("answer_question", END)

        # Direct edges for other actions
        workflow.add_edge("add_document", END)
        workflow.add_edge("remove_document", END)
        workflow.add_edge("update_document", END)

        # Set entry point for the workflow
        workflow.set_entry_point("classify_intent")

        workflow = workflow.compile()
        return workflow
    
    def classify_intent(self, state: AgentState):
        """Classifies user intent based on input using LLM."""
        logger.info(f"Classifying intent for input: {state['user_input']}")
        prompt = CLASSIFY_INTENT_PROMPT.format(query_input=state['user_input'])
        intent = self.llm(prompt).strip().lower()
        logger.info(f"Classified intent: {intent}")
        if intent not in ["add_document", "remove_document", "search_document", "update_document", "answer_question"]:
            intent = "answer_question"
        return {"intent": intent}   

    def is_answer_question(self, state: AgentState):
        logger.info(f"The intent is {state['intent']}")
        return bool(state["intent"] == "answer_question")
    
    def add_document(self, state: AgentState):
        """Adds a document to Elasticsearch."""
        logger.info(f"Adding document with input: {state['user_input']}")
        content_parts = state["user_input"].split("|")
        if len(content_parts) < 3:
            return {"response": "Invalid format! Use: doc_id | title | content"}
        
        doc_id = content_parts[0].strip()
        title = content_parts[1].strip()
        content = content_parts[2].strip()

        chunks = chunk_text(content)
        for chunk in chunks:
            document = {
                "title": title,
                "content": chunk,
                "document_id": doc_id,
                "embedding": self.embeddings.encode(chunk),

            }
            self.es.index(index=self.index_name, body=document)
            logger.info(f"Document '{doc_id}' added.")
        return {"response":  f"Document '{title}' added with ID '{doc_id}'."}

    def remove_document(self, state: AgentState):
        """Removes a document from Elasticsearch."""
        logger.info(f"Removing document with ID: {state['user_input']}")
        doc_id = state["user_input"].split("|")[1].strip()
        body = {
            "query": {
                "match": {
                    "document_d": doc_id
                }
            }
        }
        self.es.delete(index=self.index_name, body=body)
        logger.info(f"Document '{doc_id}' removed.")
        return {"response": f"Document '{doc_id}' removed."}

    def search_document(self, state: AgentState):
        """Finds documents in Elasticsearch based on a query."""
        logger.info(f"Finding documents for query: {state['user_input']}")
        query = state["user_input"].strip()
        docs = hybrid_search(query=query, index_name=self.index_name, embeddings=self.embeddings)
        if not docs:
            logger.info("No matching documents found.")
            return {"retrieved_docs": [], "response": "No matching documents found."}
        
        logger.info(f"Found {len(docs)} documents.")
        return {"retrieved_docs": docs, "intent": state["intent"]}

    def summarize_documents(self, state: AgentState) -> AgentState:
        """Generates summaries for each retrieved document."""
        docs = state.get("retrieved_docs", [])
        summaries = []
        for doc in docs:
            prompt = PROMPT_FOR_SUMMARY.format(document=doc)
            summary = self.llm(prompt).strip()
            summaries.append(summary)
        logger.info(f"Generated {len(summaries)} summaries.")
        return {"summaries": summaries}

    def merge_summaries(self, state: AgentState) -> AgentState:
        """Merges individual summaries into a coherent final response."""
        logger.info(f"Merge summaries, state: {state}")
        summaries = state.get("summaries", [])
        if not summaries:
            return {"response": "No relevant information found."}
        
        merged_prompt = PROMPT_FOR_MERGING_SUMMARIES.format(summaries="\n".join(summaries))
        final_response = self.llm(merged_prompt).strip()
        logger.info("Final response generated.")
        return {"summarized_docs": final_response}
    
    def update_document(self, state: AgentState):
        """Updates a document in Elasticsearch."""
        logger.info(f"Updating document with input: {state['user_input']}")
        parts = state["user_input"].split("|")
        if len(parts) < 3:
            return {"response": "Invalid format! Use: update | doc_id | new_title | [optional new_content]"}
        
        doc_id = parts[1].strip()
        new_title = parts[2].strip()
        new_content = parts[3].strip() if len(parts) > 3 else None

        # Fetch the existing document
        query={
            "term": {
                "document_id":doc_id
            }
        }
        response = self.es.search(index=self.index_name, query=query)
        if response["hits"]["total"]["value"] == 0:
            return {"response": f"Document with ID '{doc_id}' not found."}
        
        # Prepare updated fields
        updated_doc = {
            "title": new_title,
        }
        if new_content:
            updated_doc.update({"content": new_content})
            updated_doc.update({"embeddings": self.embeddings.encode(new_content)})
        self.es.index(index=self.index_name, id=doc_id, body=updated_doc)
        logger.info(f"Document '{doc_id}' updated successfully.")
        return {"response": f"Document '{doc_id}' updated successfully with new title '{new_title}'."}

    def answer_question(self, state: AgentState):
        """Answers a question using RAG from retrieved documents."""
        logger.info(f"Answering question with retrieved documents.")
        logger.info(state)
        docs = state.get("summarized_docs", [])
        if not docs:
            logger.info("No documents found for answering the question.")
            return {"response": "No documents found to provide an answer."}
        
        context = "\n".join(docs)  # Join documents into a single context string
        query = state["user_input"].strip() 
        prompt = PROMPT_FOR_QA.format(context=context, query=query)
        response = self.llm(prompt)
        logger.info(f"Generated response: {response}")
        return {"response": response}

    def process_input(self, user_input: str):
        """Runs the user input through the LangGraph workflow."""
        result = self.workflow.invoke({"user_input": user_input})
        return result.get("response", "No response")
