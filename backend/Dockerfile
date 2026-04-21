FROM python:3.11-slim

WORKDIR /app

# System deps for chromadb (sqlite) + general hygiene
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend + the A2 api_functions.py that the agent reuses.
COPY backend /app/backend
COPY api_functions.py /app/api_functions.py

# Persistent volume on Railway is mounted at /data by railway.toml.
ENV VOYAGEAI_DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Railway provides $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
