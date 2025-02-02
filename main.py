from fastapi import FastAPI, HTTPException
from agent import Agent
from services.es_client import es
from config import INDEX_NAME, LLM_MODEL
from models import DocumentRequest, UpdateDocumentRequest
from services.document_ops import embeddings, hybrid_search
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


agent = Agent(es=es, index_name=INDEX_NAME, llm_model=LLM_MODEL)

# FastAPI integration
app = FastAPI()

@app.post("/process")
def process_request(user_input: str):
    """
    add_document: 'doc_id | title | content'
    remove_document: 'remove | doc_id'
    update_document: 'update | doc_id | new_title | [optional new_content]'
    """
    logger.info(f"Processing request: {user_input}")
    result = agent.workflow.invoke({"user_input": user_input})
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
