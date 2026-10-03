from __future__ import annotations

import asyncio
import json
import socket
from threading import Thread
import time

import httpx
import uvicorn

from app.main import create_app
from app.integrations.mcp_runtime import meridian_mcp_client_class
from rag.service import set_knowledge_service


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_streamable_http_mcp_discovery_and_search(built_rag_service) -> None:
    port = _free_port()
    set_knowledge_service(built_rag_service)
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.25).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.05)
        else:
            raise AssertionError("ASGI server did not become ready")

        client_class = meridian_mcp_client_class()
        mcp_client = client_class(f"http://127.0.0.1:{port}/mcp/")
        tools = asyncio.run(mcp_client.discover_tools())
        assert {tool.name for tool in tools} == {
            "search_knowledge_documents",
            "lookup_employee_profile",
            "check_pto_balance",
            "lookup_benefits_status",
            "lookup_active_assignment",
            "resolve_approval_role",
            "lookup_travel_authorization",
            "get_mock_travel_booking",
            "get_per_diem_rate",
            "get_mock_expense_claim",
        }
        tool_result = asyncio.run(
            mcp_client.call_tool(
                "search_knowledge_documents",
                {"query": "PTO notice requirement", "document_type": "policy", "top_k": 3},
            )
        )
        payload = tool_result.structuredContent
        if payload is None:
            payload = json.loads(tool_result.content[0].text)
        assert payload["status"] == "ok"
        assert len(payload["results"]) == 3
        assert payload["results"][0]["document_id"] == "MSG-POL-001"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        set_knowledge_service(None)
        assert not thread.is_alive()

