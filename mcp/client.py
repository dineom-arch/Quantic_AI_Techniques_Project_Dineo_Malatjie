"""MCP client abstraction using the official Streamable HTTP transport."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@dataclass(frozen=True)
class DiscoveredTool:
    name: str
    description: str | None


class MeridianMCPClient:
    def __init__(
        self,
        endpoint: str,
        session_id: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.session_id = session_id
        self.http_client = http_client

    def _headers(self) -> dict[str, str]:
        return {"X-Meridian-Session-Id": self.session_id} if self.session_id else {}

    @asynccontextmanager
    async def _client(self):
        if self.http_client is not None:
            original_headers = dict(self.http_client.headers)
            self.http_client.headers.update(self._headers())
            try:
                yield self.http_client
            finally:
                self.http_client.headers.clear()
                self.http_client.headers.update(original_headers)
        else:
            async with httpx.AsyncClient(headers=self._headers()) as client:
                yield client

    async def discover_tools(self) -> list[DiscoveredTool]:
        async with self._client() as http_client:
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

        async with self._client() as http_client:
            async with streamable_http_client(self.endpoint, http_client=http_client) as streams:
                read_stream, write_stream = streams[:2]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    return await session.call_tool(name, arguments)

