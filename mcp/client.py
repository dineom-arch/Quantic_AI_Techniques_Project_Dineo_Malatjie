"""MCP client abstraction using the official Streamable HTTP transport."""

from __future__ import annotations

from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@dataclass(frozen=True)
class DiscoveredTool:
    name: str
    description: str | None


class MeridianMCPClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    async def discover_tools(self) -> list[DiscoveredTool]:
        async with streamable_http_client(self.endpoint) as streams:
            read_stream, write_stream = streams[:2]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    DiscoveredTool(name=tool.name, description=tool.description)
                    for tool in result.tools
                ]

