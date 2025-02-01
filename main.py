import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_ollama import OllamaLLM
from elasticsearch import Elasticsearch
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from sentence_transformers import SentenceTransformer
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize components
llm = OllamaLLM(model="llama3.1")

ELASTICSEARCH_URL = "http://localhost:9200"
INDEX_NAME = "documents"

CLASSIFY_INTENT_PROMPT = """Classify the following query either in one of the following commands: 'add_document', 'remove_document', 'search_document'.
In all other cases, classify it as 'answer_question'. Please return only the intent and nothing else.

Query: {query_input}
Intent:
"""

PROMPT_FOR_QA = """
    Use the following context to answer the question:
    {context}
    
    Question: {query}
    Answer:
"""

embeddings = SentenceTransformer("all-MiniLM-L6-v2")

es = Elasticsearch(ELASTICSEARCH_URL)

class AgentState(TypedDict):
    user_input: str
    retrieved_docs: Optional[list]
    response: Optional[str]

class DocumentRequest(BaseModel):
    doc_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None


# Hybrid Search: BM25 + Vector Search
def hybrid_search(query):
    query_embedding = embeddings.encode(query).tolist()
    search_body = {
        "size": 5,
        "query": {
            "bool": {
                "should": [
                    {"match": {"content": query}},  # BM25 search
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
    results = es.search(index=INDEX_NAME, body=search_body)
    docs = []
    if results["hits"]["total"]["value"] > 0:
        for res in results["hits"]["hits"]:
            docs.append(res['_source']['content'])
    return docs


def add_document(state: AgentState) -> AgentState:
    """Adds a document to Elasticsearch."""
    logger.info(f"Adding document with input: {state['user_input']}")
    content = state["user_input"].split("|", 1)  # Format: "doc_id | content"
    if len(content) < 2:
        return {"response": "Invalid format! Use: doc_id | content"}
    doc_id, text = content
    embedding = embeddings.encode(text)
    es.index(index=INDEX_NAME, id=doc_id, body={"content": text, "embedding": embedding})
    logger.info(f"Document '{doc_id}' added.")
    return {"response": f"Document '{doc_id}' added."}

def remove_document(state: AgentState) -> AgentState:
    """Removes a document from Elasticsearch."""
    logger.info(f"Removing document with ID: {state['user_input']}")
    doc_id = state["user_input"].strip()
    es.delete(index=INDEX_NAME, id=doc_id)
    logger.info(f"Document '{doc_id}' removed.")
    return {"response": f"Document '{doc_id}' removed."}

def search_document(state: AgentState) -> AgentState:
    """Finds documents in Elasticsearch based on a query."""
    logger.info(f"Finding documents for query: {state['user_input']}")
    query = state["user_input"].strip()
    docs = hybrid_search(query=query)
    if not docs:
        logger.info("No matching documents found.")
        return {"response": "No matching documents found."}
    logger.info(f"Found {len(docs)} documents.")
    logger.info(f"Found documents. {docs}")
    return {"retrieved_docs": docs, "response": "Documents found!"}

def answer_question(state: AgentState) -> AgentState:
    """Answers a question using RAG from retrieved documents."""
    logger.info(f"Answering question: {state['user_input']}")
    query = state["user_input"].strip()
    docs = hybrid_search(query=query)
    context = "\n".join([doc for doc in docs])
    prompt = PROMPT_FOR_QA.format(context=context, query=query)
    response = llm(prompt)
    logger.info(f"Generated response: {response}")
    return {"response": response}

def classify_intent(state: AgentState) -> str:
    """Classifies user intent based on input using LLM."""
    logger.info(f"Classifying intent for input: {state['user_input']}")
    prompt = CLASSIFY_INTENT_PROMPT.format(query_input=state['user_input'])
    intent = llm(prompt).strip().lower()
    logger.info(f"Classified intent: {intent}")
    if intent not in ["add_document", "remove_document", "search_document", "answer_question"]:
        intent = "answer_question"
    return {"intent": intent}    

# Build LangGraph
workflow = StateGraph(AgentState)
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("add_document", add_document)
workflow.add_node("remove_document", remove_document)
workflow.add_node("search_document", search_document)
workflow.add_node("answer_question", answer_question)
workflow.add_conditional_edges(
    "classify_intent",
    lambda state: state["intent"],  # Use the 'intent' key from the returned dictionary
    {
        "add_document": "add_document",
        "remove_document": "remove_document",
        "search_document": "search_document",
        "answer_question": "answer_question"
    }
)

workflow.set_entry_point("classify_intent")
workflow.add_edge("add_document", END)
workflow.add_edge("remove_document", END)
workflow.add_edge("search_document", END)
workflow.add_edge("answer_question", END)

workflow = workflow.compile()

# FastAPI integration
app = FastAPI()

@app.post("/process")
def process_request(user_input: str):
    logger.info(f"Processing request: {user_input}")
    result = workflow.invoke({"user_input": user_input})
    return {"response": result.get("response", "No response")}

@app.post("/add_document")
def add_document_api(request: DocumentRequest):
    logger.info(f"API call: add_document with {request}")
    if not request.doc_id or not request.content:
        raise HTTPException(status_code=400, detail="doc_id and content are required")
    embedding = embeddings.encode(request.content)
    result = es.index(index=INDEX_NAME, id=request.doc_id, body={"content": request.content, "embedding": embedding})
    return {"response": result}

@app.post("/remove_document")
def remove_document_api(request: DocumentRequest):
    logger.info(f"API call: remove_document with {request}")
    if not request.doc_id:
        raise HTTPException(status_code=400, detail="doc_id is required")
    result = es.delete(index=INDEX_NAME, id=request.doc_id)
    return {"response": result}

@app.post("/search_document")
def search_document_api(query: str):
    logger.info(f"API call: search_document for query: {query}")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    docs = hybrid_search(query=query)
    if not docs:
        logger.info("No matching documents found.")
        return {"response": "No matching documents found."}
    logger.info(f"Found {len(docs)} documents.")
    logger.info(f"Found documents. {docs}")
    return {"retrieved_docs": docs, "response": "Documents found!"}

@app.get("/")
def home():
    logger.info("API home endpoint accessed.")
    return {"message": "LangGraph Elasticsearch Agent is running"}
