FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install torch cpu/cuda depending on base. Here optimizing for generic build.
# For GPU support, usually better to start FROM pytorch/pytorch base.
# But request said "Enable NVIDIA GPU resources" in docker-compose.
# To actually USE GPU, we need internal libraries.
# Let's switch base to pytorch/pytorch or install correct cuda torch.
# For simplicity in this scaffold, installing via pip (might be large).
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
