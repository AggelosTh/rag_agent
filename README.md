# rag_agent
docker run --rm --gpus all nvidia/cuda:12.6.2-runtime-ubuntu22.04 nvidia-smi

docker exec -it ollama_service bash
ollama pull orca-mini:3b

docker compose up --build