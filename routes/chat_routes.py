from fastapi import APIRouter, HTTPException
from agent import Agent
from services.es_client import es
from config import INDEX_NAME, LLM_MODEL, CHAT_HISTORY_INDEX
from typing import Dict, List
from datetime import datetime

router = APIRouter()

# Initialize chatbot agent
agent = Agent(es=es, index_name=INDEX_NAME, llm_model=LLM_MODEL)


# # Ensure the chat history index exists
if not es.indices.exists(index=CHAT_HISTORY_INDEX).body:
    es.indices.create(index=CHAT_HISTORY_INDEX)

@router.post("/chat")
def chat_endpoint(user_id: str, user_input: str):
    """
    Chat with the AI agent while maintaining conversation history in Elasticsearch.
    """
    # Retrieve past messages for context
    query = {
        "query": {
            "match": {"user_id": user_id}
        },
        "size": 5,  # Retrieve the last 5 messages for context
        "sort": [{"timestamp": "desc"}]
    }
    response = es.search(index=CHAT_HISTORY_INDEX, body=query)
    if response["hits"]["total"]["value"] > 0:
        chat_history = response["hits"]["hits"]

        # Build context
        context = "\n".join([
            f"User: {entry['_source']['user_input']} \nBot: {entry['_source']['bot_response']}"
            for entry in chat_history
        ])
        full_input = f"Context:\n{context}\n\nUser: {user_input}\nBot:"
    else:
        full_input = ""    

    # Get response from agent
    bot_response = agent.workflow.invoke({"user_input": full_input}).get("response", "No response")

    # Store the conversation in Elasticsearch
    doc = {
        "user_id": user_id,
        "user_input": user_input,
        "bot_response": bot_response,
        "timestamp": datetime.now()
    }
    es.index(index=CHAT_HISTORY_INDEX, body=doc)

    return {"response": bot_response}


@router.get("/chat/history")
def get_chat_history(user_id: str):
    """
    Retrieve chat history for a specific user from Elasticsearch.
    """
    query = {
        "query": {
            "match": {"user_id": user_id}
        },
        "size": 50,  # Limit the retrieval
        "sort": [{"timestamp": "asc"}]
    }
    response = es.search(index=CHAT_HISTORY_INDEX, body=query)
    chat_history = [{"user": entry["_source"]["user_input"], "bot": entry["_source"]["bot_response"]}
                    for entry in response["hits"]["hits"]]

    return {"history": chat_history}


@router.delete("/chat/history")
def clear_chat_history(user_id: str):
    """
    Delete chat history for a specific user in Elasticsearch.
    """
    try:
        query = {
            "query": {
                "match": {"user_id": user_id}
            }
        }
        es.delete_by_query(index=CHAT_HISTORY_INDEX, body=query)
        return {"response": f"Chat history for user {user_id} cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
