from pathlib import Path

import pytest

from app.config import REPOSITORY_ROOT
from rag.service import KnowledgeService


@pytest.fixture(scope="session")
def built_rag_service() -> KnowledgeService:
    service = KnowledgeService(
        REPOSITORY_ROOT / "knowledge",
        REPOSITORY_ROOT / "runtime_data" / "rag_index",
    )
    assert service.load(), service.error
    return service

