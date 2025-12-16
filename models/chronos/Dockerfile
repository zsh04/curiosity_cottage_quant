FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (git for pip install git+...)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install chronos-forecasting from source as per official instructions for Chronos (Standard) usage
RUN pip install --no-cache-dir git+https://github.com/amazon-science/chronos-forecasting.git

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
