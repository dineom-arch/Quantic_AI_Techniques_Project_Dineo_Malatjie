"""Knowledge tool registration.

The Phase-1 handler is intentionally non-substantive. Phase 2 will connect it
to canonical corpus retrieval while preserving this controlled tool name.
"""

from typing import Any


def register_knowledge_tools(server: Any) -> None:
    @server.tool()
    async def search_knowledge_documents(
        query: str,
        document_type: str = "all",
        top_k: int = 5,
        topic: str | None = None,
    ) -> dict[str, object]:
        """Search approved canonical documents (Phase-2 implementation pending)."""

        del query, document_type, top_k, topic
        return {
            "status": "dependency_unavailable",
            "results": [],
            "message": "Canonical knowledge retrieval is deferred to Phase 2.",
        }

