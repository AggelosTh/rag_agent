from services.es_client import es
from langchain.text_splitter import RecursiveCharacterTextSplitter

import nltk
from nltk.corpus import wordnet
# Download NLP resources
nltk.download("wordnet")
nltk.download("omw-1.4")

CHUNK_SIZE = 512  # Define chunk size (in characters)
OVERLAP = 51  # Define overlap size

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,  # Max tokens per chunk
    chunk_overlap=OVERLAP,  # 10% overlap
    # length_function=count_tokens  # Use BAAI tokenizer
)

def expand_query(query: str) -> list:
    words = query.split()
    expanded_terms = set(words)
    
    for word in words:
        synonyms = wordnet.synsets(word)
        for syn in synonyms:
            for lemma in syn.lemmas():
                expanded_terms.add(lemma.name().replace("_", " "))

    return list(expanded_terms)


def hybrid_search(query, index_name, embeddings):
    expanded_queries = expand_query(query)
    query_embedding = embeddings.encode(query).tolist()

    search_body = {
        "size": 2,
        "query": {
            "bool": {
                "should": [
                    {"match": {"content": query}},  # Original BM25
                    *[{"match": {"content": q}} for q in expanded_queries],  # Synonyms
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
    
    results = es.search(index=index_name, body=search_body)
    return [res["_source"]["content"] for res in results["hits"]["hits"]]


def chunk_text(text: str) -> list[str]:
    chunks = text_splitter.split_text(text)
    return chunks