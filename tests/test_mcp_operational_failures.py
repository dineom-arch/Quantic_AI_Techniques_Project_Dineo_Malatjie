from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
import socket
from threading import Thread
import time

import httpx
import pytest
import uvicorn

from app.config import get_settings
from app.identity.runtime import session_store
from app.integrations.mcp_runtime import meridian_mcp_client_class
from app.main import create_app


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _call_with_configured_data() -> dict:
    get_settings.cache_clear()
    session_store.reset()
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error")
    )
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{base_url}/auth/identities", timeout=0.25).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.05)
        else:
            raise AssertionError("ASGI server did not become ready")

        session_id = httpx.post(
            f"{base_url}/auth/session", json={"corporate_username": "naledi.molefe"}
        ).json()["session_id"]
        client = meridian_mcp_client_class()(
            f"{base_url}/mcp/", session_id=session_id
        )
        result = asyncio.run(client.call_tool("check_pto_balance", {"target": "self"}))
        return result.structuredContent or json.loads(result.content[0].text)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        session_store.reset()
        get_settings.cache_clear()
        assert not thread.is_alive()


def _temporary_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "mock_data"
    shutil.copytree(Path("mock_data/hr_operations"), root / "hr_operations")
    return root


@pytest.mark.parametrize("failure_kind", ["missing", "malformed"])
def test_operational_dependency_failure_crosses_real_mcp_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
) -> None:
    root = _temporary_fixture_root(tmp_path)
    employees_path = root / "hr_operations" / "employees.json"
    if failure_kind == "missing":
        employees_path.unlink()
    else:
        employees_path.write_text("{malformed", encoding="utf-8")
    monkeypatch.setenv("MOCK_DATA_PATH", str(root))

    payload = _call_with_configured_data()

    assert payload["status"] == "dependency_unavailable"
    serialized = json.dumps(payload)
    assert "Traceback" not in serialized
    assert str(tmp_path) not in serialized
    assert "employees.json" in payload["message"]
