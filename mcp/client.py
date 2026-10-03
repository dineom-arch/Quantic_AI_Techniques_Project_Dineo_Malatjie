"""MCP client abstraction using the official Streamable HTTP transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@dataclass(frozen=True)
class DiscoveredTool:
    name: str
    description: str | None


class MeridianMCPClient:
    def __init__(self, endpoint: str, session_id: str | None = None) -> None:
        self.endpoint = endpoint
        self.session_id = session_id

    def _headers(self) -> dict[str, str]:
        return {"X-Meridian-Session-Id": self.session_id} if self.session_id else {}

    async def discover_tools(self) -> list[DiscoveredTool]:
        async with httpx.AsyncClient(headers=self._headers()) as http_client:
            async with streamable_http_client(self.endpoint, http_client=http_client) as streams:
                read_stream, write_stream = streams[:2]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [
                        DiscoveredTool(name=tool.name, description=tool.description)
                        for tool in result.tools
                    ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        """Invoke a discovered MCP tool across Streamable HTTP."""

        async with httpx.AsyncClient(headers=self._headers()) as http_client:
            async with streamable_http_client(self.endpoint, http_client=http_client) as streams:
                read_stream, write_stream = streams[:2]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    return await session.call_tool(name, arguments)

