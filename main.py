from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent import Agent
from services.es_client import es
from config import INDEX_NAME, LLM_MODEL
from models import DocumentRequest
from services.document_ops import embeddings, hybrid_search
from services.text_utils import chunk_text

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent = Agent(es=es, index_name=INDEX_NAME, llm_model=LLM_MODEL)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process")
def process_request(user_input: str):
    """
    remove_document: 'remove | doc_id'
    """
    logger.info(f"Processing request: {user_input}")
    result = agent.workflow.invoke({"user_input": user_input})
    return {"response": result.get("response", "No response")}

@app.post("/add_document")
def add_document_api(request: DocumentRequest):
    logger.info(f"API call: add_document with {request}")
    if not request.doc_id or not request.content or not request.title:
        raise HTTPException(status_code=400, detail="doc_id, content, and title are required")

    content = request.content.replace('\n', '')
    content = content.replace('"', '')
    chunks = chunk_text(content)

    for chunk in chunks:
        # Create a document dictionary
        document = {
            "title": request.title,
            "content": chunk,
            "document_id": request.doc_id,
            "embedding": embeddings.encode(chunk)
        }
        es.index(index='_'.join([INDEX_NAME, 'chunks']), body=document)
    return {"response": f"Document '{request.title}' added with ID '{request.doc_id}'."}

@app.post("/remove_document")
def remove_document_api(request: DocumentRequest):
    logger.info(f"API call: remove_document with {request}")
    if not request.doc_id:
        raise HTTPException(status_code=400, detail="doc_id is required")
    body = {
        "query": {
            "match": {
                "document_id": request.doc_id
            }
        }
    }
    result = es.delete_by_query(index=INDEX_NAME, body=body)
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
    return {"message": "LangGraph Agent is running"}
