"""Contract-defined knowledge retrieval over the approved corpus."""

from typing import Any

from rag.retriever import RetrievalValidationError
from rag.service import get_knowledge_service


def register_knowledge_tools(server: Any, service_provider=get_knowledge_service) -> None:
    @server.tool()
    async def search_knowledge_documents(
        query: str,
        document_type: str = "all",
        top_k: int = 5,
        topic: str | None = None,
    ) -> dict[str, object]:
        """Retrieve authoritative evidence without making a policy decision."""

        service = service_provider()
        if not service.is_ready:
            return {"status": "dependency_unavailable", "results": [], "message": service.error}
        try:
            results = service.search(
                query,
                top_k=top_k,
                document_type=document_type,
                topic=topic,
            )
        except RetrievalValidationError as exc:
            return {"status": "invalid_request", "results": [], "message": str(exc)}
        except Exception as exc:
            return {"status": "dependency_unavailable", "results": [], "message": str(exc)}
        return {
            "status": "ok" if results else "not_found",
            "results": [
                {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "title": result.title,
                    "document_type": result.document_type,
                    "topic": result.topic,
                    "section": result.section,
                    "snippet": result.text,
                    "score": result.score,
                    "effective_date": result.effective_date,
                    "version": result.version,
                    "owner": result.owner,
                    "status": result.status,
                    "source_path": result.source_path,
                }
                for result in results
            ],
        }

