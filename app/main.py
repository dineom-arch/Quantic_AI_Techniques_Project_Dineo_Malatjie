"""Meridian Compass Phase-1 FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.ui import router as ui_router
from app.config import REPOSITORY_ROOT
from app.integrations.mcp_runtime import create_mcp_server
from app.llm.provider import get_llm_provider


_DEFAULT_PROVIDER = object()


def create_app(llm_provider=_DEFAULT_PROVIDER) -> FastAPI:
    mcp_server, mcp_app = create_mcp_server()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with mcp_server.session_manager.run():
            yield

    application = FastAPI(
        title="Meridian Compass",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(auth_router)
    application.include_router(chat_router)
    application.include_router(health_router)
    application.include_router(ui_router)
    application.mount(
        "/static", StaticFiles(directory=REPOSITORY_ROOT / "app" / "static"),
        name="static",
    )
    application.mount("/mcp", mcp_app)
    application.state.mcp_server = mcp_server
    application.state.llm_provider = (
        get_llm_provider() if llm_provider is _DEFAULT_PROVIDER else llm_provider
    )
    return application


app = create_app()

