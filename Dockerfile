FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000 \
    KNOWLEDGE_DATA_PATH=/app/knowledge \
    MOCK_DATA_PATH=/app/mock_data \
    VECTOR_STORE_PATH=/app/runtime_data/rag_index \
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

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

