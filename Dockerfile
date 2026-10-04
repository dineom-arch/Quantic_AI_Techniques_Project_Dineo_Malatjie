FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000 \
    KNOWLEDGE_DATA_PATH=/app/knowledge \
    MOCK_DATA_PATH=/app/mock_data \
    VECTOR_STORE_PATH=/app/data/vector_store \
    HF_HOME=/app/.cache/huggingface \
    MCP_TRANSPORT=streamable-http \
    LOG_LEVEL=INFO

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY mcp ./mcp
COPY rag ./rag
COPY knowledge ./knowledge
COPY data ./data
COPY mock_data ./mock_data
COPY scripts ./scripts

# Build the canonical index from the approved corpus inside the image. This
# avoids relying on gitignored workstation artefacts at runtime and also
# retains the embedding model files used to validate and query the index.
RUN python scripts/build_index.py

# Runtime retrieval must use the model bundled during the deterministic image
# build rather than attempting an external model download on application start.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

