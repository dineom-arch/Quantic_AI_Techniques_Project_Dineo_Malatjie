from __future__ import annotations

import asyncio
import socket
from threading import Thread
import time

import httpx
import uvicorn

from app.main import create_app
from app.integrations.mcp_runtime import meridian_mcp_client_class


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_streamable_http_mcp_discovery() -> None:
    port = _free_port()
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
        tools = asyncio.run(client_class(f"http://127.0.0.1:{port}/mcp/").discover_tools())
        assert [tool.name for tool in tools] == ["search_knowledge_documents"]
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()

