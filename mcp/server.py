"""Official MCP SDK server configured for Streamable HTTP.

This top-level directory intentionally is not a Python package because its
controlled name is the same as the official SDK's ``mcp`` package.
"""

import importlib.util
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def _knowledge_registrar():
    path = Path(__file__).resolve().parent / "tools" / "knowledge.py"
    spec = importlib.util.spec_from_file_location("_meridian_mcp_knowledge_tools", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Unable to load MCP knowledge tools: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.register_knowledge_tools


def create_mcp_server() -> tuple[FastMCP, object]:
    """Create a fresh server and ASGI app with an independent lifespan."""

    server = FastMCP(
        "meridian-compass-mcp",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
    )
    _knowledge_registrar()(server)
    return server, server.streamable_http_app()


mcp_server, mcp_app = create_mcp_server()


if __name__ == "__main__":
    mcp_server.run(transport="streamable-http")

