"""Meridian Compass Phase-1 FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.integrations.mcp_runtime import create_mcp_server


def create_app() -> FastAPI:
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
    application.mount("/mcp", mcp_app)
    application.state.mcp_server = mcp_server
    return application


app = create_app()

