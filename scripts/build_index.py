"""Build or rebuild the local canonical Markdown FAISS index."""

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import get_settings  # noqa: E402
from rag.service import KnowledgeService  # noqa: E402


def main() -> int:
    settings = get_settings()
    service = KnowledgeService(settings.knowledge_data_path, settings.vector_store_path)
    result = service.build()
    print(f"documents={result.document_count}")
    print(f"policies={result.policy_count}")
    print(f"procedures={result.procedure_count}")
    print(f"chunks={result.chunk_count}")
    print(f"index_path={result.index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
