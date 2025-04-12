ELASTICSEARCH_URL = "http://localhost:9200"
INDEX_NAME = "test"
LLM_MODEL = "llama3.1"
EMBEDDINGS_MODEL = "BAAI/bge-large-en"

CLASSIFY_INTENT_PROMPT = """Analyze the user's message and determine what document operation they want to perform.

Your task:
1. Identify the user's intention from these possibilities:
   - 'remove_document': User wants to delete/remove a document
   - 'search_document': User is looking for specific documents or information
   - 'answer_question': User is asking a general question

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
- "Delete document ABC123" → remove_document with doc_id=ABC123
- "Find me documents about neural networks" → search_document
- "What's the difference between supervised and unsupervised learning?" → answer_question

User message: {query_input}
"""

PROMPT_FOR_QA = """
    Use the following context to answer the question:
    {context}
    
    Question: {query}
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