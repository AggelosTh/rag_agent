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
llm = OllamaLLM(model="llama3.1", temperature=0.0)

ELASTICSEARCH_URL = "http://localhost:9200"
INDEX_NAME = "documents"

CLASSIFY_INTENT_PROMPT = """Classify the following query into one of the following commands: 
- 'add_document' (if the format is 'doc_id | title | content')
- 'remove_document' (if the format is 'remove | doc_id')
- 'update_document' (if the format is 'update | doc_id | new_title | [optional new_content]')
- 'search_document' (if the query is asking for information retrieval)
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

embeddings = SentenceTransformer("all-MiniLM-L6-v2", device='cuda')

es = Elasticsearch(ELASTICSEARCH_URL)

class AgentState(TypedDict):
    user_input: str
    retrieved_docs: Optional[list]
    response: Optional[str]
    doc_id: Optional[str]
    new_title: Optional[str]
    new_content: Optional[str]

class DocumentRequest(BaseModel):
    doc_id: str
    title: str
    content: str

class UpdateDocumentRequest(BaseModel):
    doc_id: str
    new_title: str
    new_content: Optional[str] = None

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
                ],
                "minimum_should_match": 1  # Ensure at least one condition matches
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
    content_parts = state["user_input"].split("|")
    if len(content_parts) < 3:
        return {"response": "Invalid format! Use: doc_id | title | content"}
    
    doc_id = content_parts[0].strip()
    title = content_parts[1].strip()
    content = content_parts[2].strip()
    document = {
        "content": content,
        "title": title,
        "embedding": embeddings.encode(content)  # Assuming you want to store embeddings as well
    }
    es.index(index=INDEX_NAME, id=doc_id, body=document)
    logger.info(f"Document '{doc_id}' added.")
    return {"response":  f"Document '{title}' added with ID '{doc_id}'."}


def remove_document(state: AgentState) -> AgentState:
    """Removes a document from Elasticsearch."""
    logger.info(f"Removing document with ID: {state['user_input']}")
    doc_id = state["user_input"].split("|")[1]
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
        return {"retrieved_docs": [], "response": "No matching documents found."}
    logger.info(f"Found {len(docs)} documents.")
    return {"retrieved_docs": docs, "response": "Documents found!"}


def update_document(state: AgentState) -> AgentState:
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
        existing_doc = es.get(index=INDEX_NAME, id=doc_id)["_source"]
    except:
        return {"response": f"Document with ID '{doc_id}' not found."}
    # Prepare updated fields
    updated_doc = {
        "title": new_title,
        "content": new_content if new_content else existing_doc["content"],  # Keep old content if not provided
        "embedding": embeddings.encode(new_content) if new_content else existing_doc["embedding"]
    }
    es.index(index=INDEX_NAME, id=doc_id, body=updated_doc)
    logger.info(f"Document '{doc_id}' updated successfully.")
    return {"response": f"Document '{doc_id}' updated successfully with new title '{new_title}'."}


def answer_question(state: AgentState) -> AgentState:
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
    response = llm(prompt)
    logger.info(f"Generated response: {response}")
    return {"response": response}


def classify_intent(state: AgentState) -> str:
    """Classifies user intent based on input using LLM."""
    logger.info(f"Classifying intent for input: {state['user_input']}")
    prompt = CLASSIFY_INTENT_PROMPT.format(query_input=state['user_input'])
    intent = llm(prompt).strip().lower()
    logger.info(f"Classified intent: {intent}")
    if intent not in ["add_document", "remove_document", "search_document", "update_document", "answer_question"]:
        intent = "answer_question"
    return {"intent": intent}    


# Build LangGraph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("add_document", add_document)
workflow.add_node("remove_document", remove_document)
workflow.add_node("search_document", search_document)
workflow.add_node("update_document", update_document)
workflow.add_node("answer_question", answer_question)

# Add conditional edges
workflow.add_conditional_edges(
    "classify_intent",
    lambda state: state["intent"],  # Use 'intent' key from classify_intent's output
    {
        "add_document": "add_document",
        "remove_document": "remove_document",
        "search_document": "search_document",
        "update_document": "update_document",
        "answer_question": "search_document"  # Route answer_question through search_document
    }
)

# Add an edge from search_document to answer_question
workflow.add_edge("search_document", "answer_question")

# Set entry point and terminal edges
workflow.set_entry_point("classify_intent")
workflow.add_edge("add_document", END)
workflow.add_edge("remove_document", END)
workflow.add_edge("update_document", END)
workflow.add_edge("search_document", END)  # This will now also lead to answer_question

# Compile workflow
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
    if not request.doc_id or not request.content or not request.title:
        raise HTTPException(status_code=400, detail="doc_id, content, and title are required")
    # Create a document dictionary
    document = {
        "id": request.doc_id,
        "content": request.content,
        "title": request.title,
        "embedding": embeddings.encode(request.content)  # Assuming you want to store embeddings as well
    }
    es.index(index=INDEX_NAME, id=request.doc_id, body=document)
    return {"response": f"Document '{request.title}' added with ID '{request.doc_id}'."}


@app.post("/remove_document")
def remove_document_api(request: DocumentRequest):
    logger.info(f"API call: remove_document with {request}")
    if not request.doc_id:
        raise HTTPException(status_code=400, detail="doc_id is required")
    result = es.delete(index=INDEX_NAME, id=request.doc_id)
    return {"response": result}


@app.post("/update_document")
def update_document_api(request: UpdateDocumentRequest):
    logger.info(f"API call: update_document with {request}")
    try:
        existing_doc = es.get(index=INDEX_NAME, id=request.doc_id)["_source"]
    except:
        raise HTTPException(status_code=404, detail=f"Document with ID '{request.doc_id}' not found.")

    updated_doc = {
        "title": request.new_title,
        "content": request.new_content if request.new_content else existing_doc["content"],
        "embedding": embeddings.encode(request.new_content) if request.new_content else existing_doc["embedding"]
    }

    es.index(index=INDEX_NAME, id=request.doc_id, body=updated_doc)
    return {"response": f"Document '{request.doc_id}' updated successfully with new title '{request.new_title}'."}


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
