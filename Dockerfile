FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for ML libraries)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the models so they are baked into the Docker image
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Copy the rest of the app
COPY . .

# Expose the port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]