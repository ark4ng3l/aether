# AETHER v3.0 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for network recon & image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV AETHER_HOST=0.0.0.0
ENV AETHER_PORT=8000

# Create data directories
RUN mkdir -p aether/data aether/data/graphs aether/data/uploads aether/data/custom_tools

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "aether.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
