from typing import Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_ollama import OllamaLLM
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import config
from services.text_utils import hybrid_search, chunk_text
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = 'http://ollama:11434'

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
    def __init__(self, es: Elasticsearch, index_name: str, llm_model: str, use_summarization: bool = False):
        """Initialize the agent with Elasticsearch and LangChain models."""
        self.es = es
        self.index_name = index_name
        self.llm = OllamaLLM(model=llm_model, temperature=0.0, base_url=OLLAMA_BASE_URL)
        self.embeddings = SentenceTransformer(config.EMBEDDINGS_MODEL, device="cuda")
        self.use_summarization = use_summarization
        
        # Create index if it doesn't exist
        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(index=index_name)


        self.workflow = self._build_workflow(

        )

    def _build_workflow(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("remove_document", self.remove_document)
        workflow.add_node("search_document", self.search_document)
        workflow.add_node("summarize_documents", self.summarize_documents)
        workflow.add_node("merge_summaries", self.merge_summaries)
        workflow.add_node("answer_question", self.answer_question)

        # Conditional edges from classify_intent
        workflow.add_conditional_edges(
            "classify_intent",
            lambda state: state["intent"],
            {
                "remove_document": "remove_document",
                "search_document": "search_document",
                "answer_question": "search_document",
            }
        )
        if self.use_summarization:
            workflow.add_edge("search_document", "summarize_documents")
            workflow.add_edge("summarize_documents", "merge_summaries")
            workflow.add_edge("merge_summaries", "answer_question")
        else:
            workflow.add_conditional_edges(
                "search_document",
                lambda state: self.is_answer_question(state),
                {True: "answer_question", False: END}  # If not answer_question, stop after search
            )

        workflow.add_edge("remove_document", END)
        workflow.add_edge("answer_question", END)

        # Set entry point for the workflow
        workflow.set_entry_point("classify_intent")

        workflow = workflow.compile()
        return workflow
    
    def classify_intent(self, state: AgentState):
        """Classifies user intent based on input using LLM."""
        logger.info(f"Classifying intent for input: {state['user_input']}")
        prompt = config.CLASSIFY_INTENT_PROMPT.format(query_input=state['user_input'])
        intent = self.llm.invoke(prompt).strip().lower()
        logger.info(f"Classified intent: {intent}")
        if intent not in ["add_document", "search_document", "answer_question"]:
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
        self.es.delete_by_query(index=self.index_name, body=body)
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
        return {"retrieved_docs": [doc["content"] for doc in docs], "intent": state["intent"], "response": [doc["title"] for doc in docs]}

    def summarize_documents(self, state: AgentState) -> AgentState:
        """Generates summaries for each retrieved document."""
        logger.info(f"Generate summaries.")
        docs = state.get("retrieved_docs", [])
        summaries = []
        for doc in docs:
            prompt = config.PROMPT_FOR_SUMMARY.format(document=doc)
            summary = self.llm.invoke(prompt).strip()
            summaries.append(summary)
        return {"summaries": summaries}

    def merge_summaries(self, state: AgentState) -> AgentState:
        """Merges individual summaries into a coherent final response."""
        logger.info(f"Merging summaries")
        summaries = state.get("summaries", [])
        if not summaries:
            return {"response": "No relevant information found."}
        
        merged_prompt = config.PROMPT_FOR_MERGING_SUMMARIES.format(summaries="\n".join(summaries))
        final_response = self.llm.invoke(merged_prompt).strip()
        logger.info("Final response generated.")
        return {"summarized_docs": final_response}
    

    def answer_question(self, state: AgentState):
        """Answers a question using RAG from retrieved documents."""
        logger.info(f"Answering question with retrieved documents.")
        logger.info(state)
        if self.use_summarization:
            docs = state.get("summarized_docs", [])
        else:
            docs = state.get("retrieved_docs", [])    
        if not docs:
            logger.info("No documents found for answering the question.")
            return {"response": "No documents found to provide an answer."}
        
        context = "\n".join(docs)  # Join documents into a single context string
        query = state["user_input"].strip() 
        prompt = config.PROMPT_FOR_QA.format(context=context, query=query)
        response = self.llm.invoke(prompt)
        logger.info(f"Generated response: {response}")
        return {"response": response}

    def process_input(self, user_input: str):
        """Runs the user input through the LangGraph workflow."""
        result = self.workflow.invoke({"user_input": user_input})
        return result.get("response", "No response")
