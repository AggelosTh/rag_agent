# RAG Agent 🚀

A Retrieval-Augmented Generation (RAG) system that integrates with **Elasticsearch** to provide accurate, context-aware answers.\
It allows you to **add documents**, **retrieve them via queries**, **summarize results**, and **merge summaries** into more precise responses.

---

## Features

- Add and manage documents in Elasticsearch
- Retrieve relevant documents with natural language queries
- Generate concise summaries of retrieved documents
- Merge results for improved accuracy
- Fully containerized with **Docker Compose**
- ⚙Powered by **LangGraph**, **FastAPI**, and **Ollama (Llama3:8B)**

---

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- [LangGraph](https://www.langchain.com/langgraph)
- [Elasticsearch](https://www.elastic.co/elasticsearch/)
- [Ollama](https://ollama.ai/) with **Llama3.1:8B**
- [Docker Compose](https://docs.docker.com/compose/)

---

## Getting Started

### 1. Verify GPU Access

Make sure your system detects the GPU properly:

```bash
docker run --rm --gpus all nvidia/cuda:12.6.2-runtime-ubuntu22.04 nvidia-smi
```

### 2. Pull the Model

Access the Ollama container and pull **Llama3.1:8B**:

```bash
docker exec -it ollama_service bash
ollama pull llama3.1:8b
```

### 3. Run the Services

Build and start the stack:

```bash
docker compose up --build
```

### 4. Set up the UI

Navigate to the UI directory and install the dependencies:

```bash
cd rag-agent-ui
npm install framer-motion lucide-react axios
npm install -D tailwindcss@3
npx tailwindcss init -p
npm start

```
