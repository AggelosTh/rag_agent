ELASTICSEARCH_URL = "http://elasticsearch:9200"
INDEX_NAME = "chunks"
# LLM_MODEL = "llama3.1"
LLM_MODEL = "orca-mini:3b"
# EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"
EMBEDDINGS_MODEL = "BAAI/bge-large-en"

CLASSIFY_INTENT_PROMPT = """You are an intent classification assistant.

Classify the user's query into **one** of the following intents:

- `remove_document`: if the query is a command to remove a document, typically in the format "remove | doc_id" or similar.
- `search_document`: if the query is asking to search, list, or retrieve documents.
- `answer_question`: for all other types of queries, such as general questions or instructions that do not match the above two patterns.

Return only the intent name (exactly as shown), with no explanation or extra text.

Query: {query_input}
Intent:
"""

PROMPT_FOR_QA = """
You are a helpful assistant. Use the provided context to answer the question as accurately as possible.

Context:
{context}

Question:
{query}

Instructions:
- If the answer is clearly stated in the context, provide a direct and concise answer.
- If the question is relevant to the context but the answer is **not fully available**, say so and explain briefly.
- If the question is **not related** to the context at all, politely state that the context does not contain relevant information.

Answer:
"""

PROMPT_FOR_SUMMARY = """
Summarize the following document in a concise manner, keeping key information:

Document:
{document}

Summary:
"""

PROMPT_FOR_MERGING_SUMMARIES = """
Given the following document summaries, generate a final structured response that combines key points, removes redundancy, and ensures coherence:

Summaries:
{summaries}

Final Answer:
"""