from typing import List, Dict, Any
from models import *
from langgraph.graph import StateGraph, END
from langchain_ollama import OllamaLLM
from sentence_transformers import SentenceTransformer
from services.text_utils import expand_query
import config
import json
from elasticsearch import Elasticsearch
import logging

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
        self.index_name = index_name
        self.llm = OllamaLLM(model=llm_model, temperature=0.0, base_url=OLLAMA_BASE_URL)
        self.embeddings = config.embeddings
        self.use_summarization = use_summarization
        self.es = es

        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(index=index_name)

        self.workflow = self._build_workflow()

    def search_elasticsearch(self, query: str, intent: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for documents in Elasticsearch using hybrid retrieval (BM25 + vector search)."""
        expanded_queries = expand_query(query)
        query_embedding = self.embeddings.encode(query).tolist()
        
        # Build hybrid search query
        hybrid_query = {
        "size": k,
        "query": {
            "bool": {
                "should": [
                    {"match": {"content": query}},
                    *[{"match": {"content": q}} for q in expanded_queries],
                    {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": query_embedding}
                            }
                        }
                    }
                ]
            }
        }
    }
        
        try:
            response = self.es.search(index=self.index_name, body=hybrid_query)
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "doc_id": hit["_id"],
                    "title": hit["_source"].get("title", ""),
                    "content": hit["_source"].get("content", ""),
                    "score": hit["_score"]
                })
        except Exception as e:
            logger.error(f"Elasticsearch search error: {e}")
            return []
        if results:
            if intent == "search_document":
                document = self.es.get(index=self.index_name, id=results["doc_id"]) # TODO needs fix
                return document
            return results
        return []

    # @tool
    def remove_document_from_elasticsearch(self, doc_id: str) -> Dict[str, Any]:
        """Remove a document from Elasticsearch by its ID."""
        try:
            # Check if document exists
            exists = self.es.exists(index=self.index_name, id=doc_id)
            if not exists:
                return {
                    "status": "error",
                    "message": f"Document {doc_id} not found"
                }
            
            # Delete the document
            response = self.es.delete(
                index=self.index_name,
                id=doc_id,
                refresh=True
            )
            
            return {
                "status": "success",
                "message": f"Document {doc_id} removed successfully",
                "result": response
            }
        except Exception as e:
            logger.error(f"Failed to remove document: {e}")
            return {
                "status": "error",
                "message": f"Failed to remove document: {str(e)}"
            }

    def _build_workflow(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("remove_document", self.remove_document)
        workflow.add_node("search_document", self.search_document)
        workflow.add_node("summarize_documents", self.summarize_documents)
        workflow.add_node("merge_summaries", self.merge_summaries)
        workflow.add_node("answer_question", self.answer_question)
        
        # Add conditional edges from intent classifier
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
            workflow.add_conditional_edges(
                "search_document",
                lambda state: state["intent"],
                {
                    "search_document": END,  # Stop after search_document for search_document intent
                    "answer_question": "summarize_documents"  # Proceed to summarization for answer_question intent
                }
            )
            workflow.add_edge("summarize_documents", "merge_summaries")
            workflow.add_edge("merge_summaries", "answer_question")
        else:
            workflow.add_conditional_edges(
                "search_document",
                lambda state: state["intent"],
                {
                    "search_document": END,  # Stop after search_document for search_document intent
                    "answer_question": "answer_question"  # Proceed to answer_question for answer_question intent
                }
            )
        
        workflow.add_edge("answer_question", END)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        return workflow.compile()

    def classify_intent(self, state: AgentState) -> AgentState:
        """Classify user intent and extract structured information using natural language understanding."""
        user_input = state["user_input"].strip()
        prompt = config.CLASSIFY_INTENT_PROMPT.format(query_input=user_input)
        
        try:
            # Get LLM response
            response = self.llm(prompt).strip()
            logger.info(f"Intent classification response: {response}")
            
            # Parse the JSON response
            extracted_info = json.loads(response)
            intent = extracted_info.get("intent", "answer_question")
            
            # Log the extracted information
            logger.info(f"Extracted intent: {intent}")
            logger.info(f"Extracted doc_id: {extracted_info.get('doc_id', '')}")
            
            return {
                "intent": intent,
                "doc_id": extracted_info.get("doc_id", ""),
                "new_title": extracted_info.get("title", ""),
                "new_content": extracted_info.get("content", ""),
                "extracted_info": extracted_info
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.error(f"Raw response: {response}")
            # Fall back to answer_question on parse error
            return {"intent": "answer_question"}
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return {"intent": "answer_question"}

    def remove_document(self, state: AgentState) -> AgentState:
        """Handle removing a document using the Elasticsearch tool."""
        doc_id = state.get("doc_id", "")
        
        # Validate required fields
        if not doc_id:
            return {"response": "Error: Document ID is required to remove a document."}
        
        # Remove document
        result = self.remove_document_from_elasticsearch(doc_id)
        
        # Generate response
        if result.get("status") == "success":
            response = f"Successfully removed document '{doc_id}'."
        else:
            response = f"Failed to remove document: {result.get('message', 'Unknown error')}"
        
        return {"response": response}

    def search_document(self, state: AgentState) -> AgentState:
        """Search for documents using the Elasticsearch tool."""
        query = state["user_input"].strip()
        intent = state["intent"]
        docs = self.search_elasticsearch(query=query, intent=intent)
        
        if not docs:
            logger.info("No matching documents found.")
            return {"retrieved_docs": [], "response": "No matching documents found."}
        
        logger.info(f"Found {len(docs)} documents.")
        return {"retrieved_docs": [doc for doc in docs], "intent": state["intent"], "response": [doc["title"] for doc in docs]}

    def summarize_documents(self, state: AgentState) -> AgentState:
        """Generates summaries for each retrieved document."""
        logger.info(f"Generate summaries.")
        docs = state.get("retrieved_docs", [])
        summaries = []
        
        for doc in docs:
            prompt = config.PROMPT_FOR_SUMMARY.format(document=doc)
            summary = self.llm.invoke(prompt).strip()
            summaries.append(summary)
        
        logger.info(f"Generated {len(summaries)} summaries.")
        return {"summaries": summaries}

    def merge_summaries(self, state: AgentState) -> AgentState:
        """Merges individual summaries into a coherent final response."""
        logger.info("Merging summaries")
        summaries = state.get("summaries", [])
        
        if not summaries:
            return {"response": "No relevant information found to answer your question."}
        
        merged_prompt = config.PROMPT_FOR_MERGING_SUMMARIES.format(summaries="\n".join(summaries))
        final_response = self.llm.invoke(merged_prompt).strip()
        logger.info("Final response generated.")
        return {"summarized_docs": final_response}
    

    def answer_question(self, state: AgentState):
        """Answers a question using RAG from retrieved documents."""
        logger.info("Answering question with retrieved documents.")
        
        if self.use_summarization:
            context = state.get("summarized_docs", "")
            if not context:
                return {"response": "I couldn't find any relevant information to answer your question."}
        else:
            docs = state.get("retrieved_docs", [])
            if not docs:
                logger.info("No documents found for answering the question.")
                return {"response": "I couldn't find any documents with information to answer your question."}
            
            # Format documents as context
            context_parts = []
            for doc in docs:
                doc_id = doc.get("doc_id", "")
                title = doc.get("title", "")
                content = doc.get("content", "")
                doc_context = f"Document ID: {doc_id}\nTitle: {title}\n\nContent:\n{content}\n"
                context_parts.append(doc_context)
            
            context = "\n---\n".join(context_parts)
        
        # Generate answer using context and query
        query = state["user_input"].strip()
        prompt = config.PROMPT_FOR_QA.format(context=context, query=query)
        response = self.llm(prompt)
        
        logger.info("Generated response to user query.")
        return {"response": response}

    def process_input(self, user_input: str) -> str:
        """Runs the user input through the LangGraph workflow."""
        try:
            result = self.workflow.invoke({"user_input": user_input})
            return result.get("response", "I'm sorry, I couldn't process your request.")
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return f"I encountered an error while processing your request: {str(e)}"