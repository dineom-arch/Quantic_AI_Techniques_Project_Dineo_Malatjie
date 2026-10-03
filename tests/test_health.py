from fastapi.testclient import TestClient

from app.main import create_app
from rag.service import KnowledgeService, set_knowledge_service


def test_health_reports_degraded_when_rag_is_unavailable(tmp_path) -> None:
    unavailable = KnowledgeService(tmp_path / "missing-corpus", tmp_path / "missing-index")
    unavailable.load()
    set_knowledge_service(unavailable)
    try:
        with TestClient(create_app()) as client:
            response = client.get("/health")
    finally:
        set_knowledge_service(None)

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "application": "meridian-compass",
        "mcp": "connected",
        "rag": "not_ready",
    }


def test_health_reports_ready_when_rag_is_loaded(built_rag_service) -> None:
    set_knowledge_service(built_rag_service)
    try:
        with TestClient(create_app()) as client:
            response = client.get("/health")
    finally:
        set_knowledge_service(None)

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "meridian-compass",
        "mcp": "connected",
        "rag": "ready",
    }


def test_chat_orchestration_uses_canonical_v12_schema() -> None:
    with TestClient(create_app()) as client:
        session = client.post(
            "/auth/session", json={"corporate_username": "naledi.molefe"}
        ).json()
        response = client.post(
            "/chat",
            json={"message": "What is my PTO balance?", "session_id": session["session_id"]},
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"answer", "status", "citations", "source_snippets", "tool_trace"}
    assert payload["status"] == "tool_error"
    assert payload["citations"] == []
    assert payload["source_snippets"] == []
    assert "no policy answer was generated" in payload["answer"].lower()

