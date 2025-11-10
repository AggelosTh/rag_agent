from sentence_transformers import SentenceTransformer

ELASTICSEARCH_URL = "http://elasticsearch:9200"
INDEX_NAME = "chunks"
LLM_MODEL = "llama3.1:8b"
EMBEDDINGS_MODEL = "BAAI/bge-large-en"

embeddings = SentenceTransformer(EMBEDDINGS_MODEL, device="cuda")

CLASSIFY_INTENT_PROMPT = """You are an intent classification assistant.

Classify the user's query into **one** of the following intents:

Your task:
1. Identify the user's intention from these possibilities:
   - 'remove_document': User wants to delete/remove a document
   - 'search_document': User is asking to search, list, or retrieve documents.
   - 'answer_question': For all other types of queries, such as general questions or instructions that do not match the above two patterns.

2. Extract any relevant information based on the intent:
   - doc_id: Any document identifier mentioned (like DOC123, #A456, etc.)
   - title: Any document title or name mentioned
   - content: Any document content or text the user wants to add/update

3. Return a JSON object with the following structure:
{{
  "intent": the_identified_intent,
  "doc_id": the extracted_document_id,
  "title": the extracted_document_title,
  "content": the extracted_document_content"
}}

Respond only with the JSON. Fields that aren't mentioned should be empty strings.

Examples of how different requests should be understood:
- "Find me documents about neural networks" → search_document
- "What's the difference between supervised and unsupervised learning?" → answer_question

User message: {query_input}
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