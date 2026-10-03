from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_phase_one_readiness() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "application": "meridian-compass",
        "mcp": "connected",
        "rag": "not_ready",
    }


def test_chat_placeholder_uses_canonical_v12_schema() -> None:
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
    assert payload["status"] == "insufficient_evidence"
    assert payload["citations"] == []
    assert payload["source_snippets"] == []

