ELASTICSEARCH_URL = "http://elasticsearch:9200"
INDEX_NAME = "chunks"
LLM_MODEL = "llama3.1"
# EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"
EMBEDDINGS_MODEL = "BAAI/bge-large-en"

CLASSIFY_INTENT_PROMPT = """Classify the following query into one of the following commands: 
- 'add_document' (if the format is 'doc_id | title | content')
- 'remove_document' (if the format is 'remove | doc_id')
- 'update_document' (if the format is 'update | doc_id | new_title | [optional new_content]')
- 'search_document' (if the query is asking for a document)
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