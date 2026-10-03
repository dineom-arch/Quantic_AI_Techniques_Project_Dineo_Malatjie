from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.identity.runtime import session_store


def test_root_serves_branded_meridian_compass_ui() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Meridian Compass" in response.text
    assert "People &amp; Travel" in response.text
    assert "Operations Assistant" in response.text
    assert "Sign in to Meridian Compass" in response.text
    assert "MSG Enterprise Identity" not in response.text


def test_ui_uses_existing_auth_chat_and_health_contracts() -> None:
    with TestClient(create_app()) as client:
        session = client.post("/auth/demo-session")
        health = client.get("/health")

    assert session.status_code == 200
    assert set(session.json()) == {"session_id", "display_name", "given_name", "job_title"}
    assert health.status_code == 200
    assert set(health.json()) == {"status", "application", "mcp", "rag"}


def test_demo_session_is_server_selected_and_supports_dynamic_greeting() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/auth/demo-session", json={"corporate_username": "liam.chen"})

    assert response.status_code == 200
    assert response.json()["given_name"] == "Naledi"


def test_ui_contains_accessible_sources_trace_and_confirmation_controls() -> None:
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    script = Path("app/static/js/compass.js").read_text(encoding="utf-8")

    assert "View sources and system trace" in script
    assert 'setAttribute("aria-label", "Verified sources")' in script
    assert "Create mock request" in script
    assert "Not now" in script
    assert "This is a demonstration action" in script
    assert 'label class="sr-only"' in html
    assert 'aria-live="polite"' in html


def test_enterprise_signin_dynamic_greeting_and_product_tour_contract() -> None:
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    script = Path("app/static/js/compass.js").read_text(encoding="utf-8")

    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert "Use your Meridian Strategy Group corporate identity" in html
    assert "Watch 1-minute tour" in html
    assert "Your 1-minute Meridian Compass tour is being prepared" in html
    assert "autoplay" not in html.casefold()
    assert "youtube" not in html.casefold() + script.casefold()
    assert "vimeo" not in html.casefold() + script.casefold()
    assert 'Hi ${givenName}, what can I help you with?' in script
    assert 'requestJson("/auth/demo-session"' in script


def test_authenticated_landing_is_open_conversation_without_prompt_cards() -> None:
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    script = Path("app/static/js/compass.js").read_text(encoding="utf-8")
    combined = html + script

    assert "prompt-card" not in combined
    assert "Example questions" not in combined
    assert "Can I take PTO during my Nairobi assignment?" not in combined
    assert "Can I extend my Nairobi trip for personal travel?" not in combined
    assert "What expenses can I claim from my business trip?" not in combined
    assert "Who needs to approve my travel request?" not in combined
    assert 'placeholder="Ask about people policy, travel or your work context…"' in html
    assert 'class="view active-view empty-state"' in html
    assert 'classList.remove("empty-state")' in script
    css = Path("app/static/css/compass.css").read_text(encoding="utf-8")
    assert ".empty-state .composer" in css
    assert "bottom: auto" in css


def test_employee_trace_uses_human_readable_completed_labels() -> None:
    script = Path("app/static/js/compass.js").read_text(encoding="utf-8")
    assert "Checked PTO balance" in script
    assert "Checked active assignment" in script
    assert "Reviewed Meridian policy" in script
    assert "Resolved approver" in script


def test_employee_facing_ui_has_no_account_chooser_or_employee_names() -> None:
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    script = Path("app/static/js/compass.js").read_text(encoding="utf-8")
    combined = (html + script).casefold()
    assert "continue with enterprise identity" in combined
    assert "choose a synthetic corporate account" not in combined
    assert "use another demo account" not in combined
    assert "switch demo user" not in combined
    assert "naledi molefe" not in combined
    assert "liam chen" not in combined


def test_same_demo_session_supports_multiple_chat_requests() -> None:
    with TestClient(create_app()) as client:
        session_id = client.post("/auth/demo-session").json()["session_id"]
        first = client.post("/chat", json={"session_id": session_id, "message": "Hello Compass"})
        second = client.post("/chat", json={"session_id": session_id, "message": "What about that trip?"})

    assert first.status_code == 200 and second.status_code == 200
    assert len(session_store.history(session_id)) == 2


def test_static_ui_contains_no_private_employee_identifiers() -> None:
    content = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            Path("app/templates/index.html"),
            Path("app/static/js/compass.js"),
            Path("app/static/css/compass.css"),
        ]
    )
    assert "EMP-" not in content
    assert "employee_id" not in content


def test_frontend_requests_are_bounded_and_loading_is_always_cleared() -> None:
    script = Path("app/static/js/compass.js").read_text(encoding="utf-8")
    assert "AbortController" in script
    assert "controller.abort()" in script
    assert 'button.disabled = false' in script
    assert '$("#loading-state").hidden = true' in script
    assert '$("#send-button").disabled = false' in script


def test_frontend_validates_restored_session_and_recovers_expired_chat_session() -> None:
    script = Path("app/static/js/compass.js").read_text(encoding="utf-8")
    assert "async function restoreSession()" in script
    assert "`/auth/session/${encodeURIComponent(saved.sessionId)}`" in script
    assert 'entry.event === "authenticated_identity_load"' in script
    assert "requireAuthentication(" in script
    assert 'sessionStorage.removeItem("meridianSession")' in script
    assert "session expired" in script


def test_chat_public_contract_remains_canonical() -> None:
    schema = create_app().openapi()["components"]["schemas"]["ChatResponse"]
    assert set(schema["properties"]) == {
        "answer", "status", "citations", "source_snippets", "tool_trace",
    }
