# Build stage
FROM python:3.10-slim-bullseye AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and cache model files
RUN mkdir -p /app/models
WORKDIR /app/models
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; AutoTokenizer.from_pretrained('microsoft/deberta-v3-base', cache_dir='/app/models'); AutoModelForSequenceClassification.from_pretrained('microsoft/deberta-v3-base', cache_dir='/app/models')"

# Runtime stage
FROM python:3.10-slim-bullseye

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy cached model files
COPY --from=builder /app/models /app/models

# Create log directories
RUN mkdir -p /logs/embedded-cluster \
    /logs/embedded-cluster-data \
    /logs/pods \
    /var/log/messages

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/models

# Expose the API port
EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
