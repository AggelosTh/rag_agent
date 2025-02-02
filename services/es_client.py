from elasticsearch import Elasticsearch
from config import ELASTICSEARCH_URL

es = Elasticsearch(ELASTICSEARCH_URL)
