from typing import Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_ollama import OllamaLLM
from sentence_transformers import SentenceTransformer
from config import CLASSIFY_INTENT_PROMPT, PROMPT_FOR_QA
from services.text_utils import hybrid_search
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


class Agent:
    def __init__(self, es, index_name, llm_model):
        """Initialize the agent with Elasticsearch and LangChain models."""
        self.es = es
        self.index_name = index_name
        self.llm = OllamaLLM(model=llm_model, temperature=0.0)
        self.embeddings = SentenceTransformer("all-MiniLM-L6-v2", device="cuda")

        # Build the LangGraph workflow
        # self.workflow = self._build_workflow()

    # def _build_workflow(self):
        """Constructs the LangGraph workflow for processing queries."""
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("add_document", self.add_document)
        workflow.add_node("remove_document", self.remove_document)
        workflow.add_node("search_document", self.search_document)
        workflow.add_node("update_document", self.update_document)
        workflow.add_node("answer_question", self.answer_question)

        # # # Add conditional edges
        workflow.add_conditional_edges(
            "classify_intent",
            lambda state: state["intent"],
            {
                "add_document": "add_document",
                "remove_document": "remove_document",
                "search_document": "search_document",
                "update_document": "update_document",
                "answer_question": "search_document"  # Route answer_question through search_document
            }
        )
        # workflow.add_conditional_edges(
        #     "search_document", self.is_answer_question, {True: "answer_question", False: END}
        # )

        workflow.add_edge("add_document", END)
        workflow.add_edge("remove_document", END)
        workflow.add_edge("update_document", END)
        workflow.add_edge("search_document", END)
        # workflow.add_edge("search_document", "answer_question")
        workflow.add_edge("answer_question", END)

        workflow.set_entry_point("classify_intent")

        self.workflow = workflow.compile()


    def classify_intent(self, state: AgentState):
        """Classifies user intent based on input using LLM."""
        logger.info(f"Classifying intent for input: {state['user_input']}")
        prompt = CLASSIFY_INTENT_PROMPT.format(query_input=state['user_input'])
        intent = self.llm(prompt).strip().lower()
        logger.info(f"Classified intent: {intent}")
        if intent not in ["add_document", "remove_document", "search_document", "update_document", "answer_question"]:
            intent = "answer_question"
        return {"intent": intent}   

    def is_answer_question(self, intent: str):
        return intent == "answer_question"

    def add_document(self, state: AgentState):
        """Adds a document to Elasticsearch."""
        logger.info(f"Adding document with input: {state['user_input']}")
        content_parts = state["user_input"].split("|")
        if len(content_parts) < 3:
            return {"response": "Invalid format! Use: doc_id | title | content"}
        
        doc_id = content_parts[0].strip()
        title = content_parts[1].strip()
        content = content_parts[2].strip()
        document = {
            "content": content,
            "title": title,
            "embedding": self.embeddings.encode(content)  # Assuming you want to store embeddings as well
        }
        self.es.index(index=self.index_name, id=doc_id, body=document)
        logger.info(f"Document '{doc_id}' added.")
        return {"response":  f"Document '{title}' added with ID '{doc_id}'."}


    def remove_document(self, state: AgentState):
        """Removes a document from Elasticsearch."""
        logger.info(f"Removing document with ID: {state['user_input']}")
        doc_id = state["user_input"].split("|")[1].strip()
        self.es.delete(index=self.index_name, id=doc_id)
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
        return {"response": docs[0]}


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
        try:
            existing_doc = self.es.get(index=self.index_name, id=doc_id)["_source"]
        except:
            return {"response": f"Document with ID '{doc_id}' not found."}
        # Prepare updated fields
        updated_doc = {
            "title": new_title,
            "content": new_content if new_content else existing_doc["content"],  # Keep old content if not provided
            "embedding": self.embeddings.encode(new_content) if new_content else existing_doc["embedding"]
        }
        self.es.index(index=self.index_name, id=doc_id, body=updated_doc)
        logger.info(f"Document '{doc_id}' updated successfully.")
        return {"response": f"Document '{doc_id}' updated successfully with new title '{new_title}'."}


    def answer_question(self, state: AgentState):
        """Answers a question using RAG from retrieved documents."""
        logger.info(f"Answering question with retrieved documents.")
        # Retrieve documents from state (assuming they are stored under 'retrieved_docs')
        docs = state.get("retrieved_docs", [])
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


# # Example Usage
# if __name__ == "__main__":
#     agent = Agent()
#     print(agent.process_input("Find me documents about AI"))
