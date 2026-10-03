"""Environment-backed application configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    """Validated settings defined by the implementation architecture contract."""

    app_env: str = "development"
    port: int = Field(default=8000, ge=1, le=65535)
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    vector_store_path: Path = REPOSITORY_ROOT / "runtime_data" / "rag_index"
    knowledge_data_path: Path = REPOSITORY_ROOT / "knowledge"
    mock_data_path: Path = REPOSITORY_ROOT / "mock_data"
    mcp_transport: str = "streamable-http"
    log_level: str = "INFO"

    @field_validator("mcp_transport")
    @classmethod
    def validate_transport(cls, value: str) -> str:
        if value != "streamable-http":
            raise ValueError("MCP_TRANSPORT must be 'streamable-http'")
        return value

    @field_validator("log_level")
    @classmethod
    def normalise_log_level(cls, value: str) -> str:
        return value.upper()


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def _path_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        port=int(os.getenv("PORT", "8000")),
        llm_api_key=_optional_env("LLM_API_KEY"),
        llm_model=_optional_env("LLM_MODEL"),
        llm_base_url=_optional_env("LLM_BASE_URL"),
        vector_store_path=_path_env(
            "VECTOR_STORE_PATH", REPOSITORY_ROOT / "runtime_data" / "rag_index"
        ),
        knowledge_data_path=_path_env("KNOWLEDGE_DATA_PATH", REPOSITORY_ROOT / "knowledge"),
        mock_data_path=_path_env("MOCK_DATA_PATH", REPOSITORY_ROOT / "mock_data"),
        mcp_transport=os.getenv("MCP_TRANSPORT", "streamable-http"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

