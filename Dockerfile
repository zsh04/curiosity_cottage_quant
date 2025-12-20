# Base Image (Lightweight)
FROM python:3.12-slim

# Enforce production settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Working Directory
WORKDIR /app

# System Dependencies (for compilation if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Application Code
COPY . .

# Set Python Path to include /app
ENV PYTHONPATH=/app

# Default Command (Overridden by docker-compose or specific run args)
CMD ["python", "run.py"]
