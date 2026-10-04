"""Static production-image guards for the canonical RAG build."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_docker_build_creates_canonical_rag_index_before_startup() -> None:
    dockerfile = (REPOSITORY_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "KNOWLEDGE_DATA_PATH=/app/knowledge" in dockerfile
    assert "MOCK_DATA_PATH=/app/mock_data" in dockerfile
    assert "VECTOR_STORE_PATH=/app/data/vector_store" in dockerfile
    assert "COPY knowledge ./knowledge" in dockerfile
    assert "COPY scripts ./scripts" in dockerfile
    assert "RUN python scripts/build_index.py" in dockerfile
    assert dockerfile.index("COPY knowledge ./knowledge") < dockerfile.index(
        "RUN python scripts/build_index.py"
    )
    assert dockerfile.index("RUN python scripts/build_index.py") < dockerfile.index(
        'CMD ["sh", "-c", "uvicorn app.main:app'
    )


def test_docker_runtime_uses_bundled_embedding_model_offline() -> None:
    dockerfile = (REPOSITORY_ROOT / "Dockerfile").read_text(encoding="utf-8")

    build_position = dockerfile.index("RUN python scripts/build_index.py")
    offline_position = dockerfile.index("HF_HUB_OFFLINE=1")
    assert "HF_HOME=/app/.cache/huggingface" in dockerfile
    assert build_position < offline_position
    assert "TRANSFORMERS_OFFLINE=1" in dockerfile


def test_docker_context_contains_all_index_build_inputs() -> None:
    dockerignore = (REPOSITORY_ROOT / ".dockerignore").read_text(encoding="utf-8")
    ignored_entries = {
        line.strip().rstrip("/")
        for line in dockerignore.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "knowledge" not in ignored_entries
    assert "rag" not in ignored_entries
    assert "scripts" not in ignored_entries
    assert "data" not in ignored_entries
    assert len(list((REPOSITORY_ROOT / "knowledge" / "policies").glob("*.md"))) == 12
    assert len(list((REPOSITORY_ROOT / "knowledge" / "procedures").glob("*.md"))) == 7
