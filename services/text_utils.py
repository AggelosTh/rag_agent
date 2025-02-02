from sentence_transformers import SentenceTransformer
from services.es_client import es
from config import INDEX_NAME
import nltk
from nltk.corpus import wordnet

# Download NLP resources
nltk.download("wordnet")
nltk.download("omw-1.4")

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
        "size": 5,
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
