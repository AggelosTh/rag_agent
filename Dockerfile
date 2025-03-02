# Use NVIDIA's CUDA base image
FROM nvidia/cuda:12.8.0-base-ubuntu22.04

# Set NVIDIA as the default runtime
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# # Install NVIDIA tools inside the container
RUN pip install nvidia-pyindex && pip install nvidia-ml-py3

# Install torch with CUDA support
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Copy requirements first (for caching)
COPY requirements.txt .

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose FastAPI's default port
EXPOSE 8000

# Start FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
