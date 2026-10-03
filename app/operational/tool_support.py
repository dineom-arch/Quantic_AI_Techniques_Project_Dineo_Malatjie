"""Shared authentication, validation, and serialization for MCP data tools."""

from datetime import date
from typing import Any

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from app.identity.models import EnterpriseIdentity
from app.identity.runtime import session_store
from app.identity.session import SessionNotFoundError


SESSION_HEADER = "x-meridian-session-id"


def resolve_identity(ctx: Context) -> EnterpriseIdentity | None:
    request = ctx.request_context.request
    session_id = request.headers.get(SESSION_HEADER) if request is not None else None
    if not session_id:
        return None
    try:
        return session_store.resolve(session_id)
    except SessionNotFoundError:
        return None


def require_self(target: str, ctx: Context) -> tuple[EnterpriseIdentity | None, dict[str, Any] | None]:
    identity = resolve_identity(ctx)
    if identity is None:
        return None, {"status": "forbidden", "message": "Authenticated session required"}
    if target != "self":
        return None, {"status": "forbidden", "message": "Only the authenticated employee is accessible"}
    return identity, None


def parse_date(value: str, field_name: str = "as_of") -> tuple[date | None, dict[str, Any] | None]:
    try:
        return date.fromisoformat(value), None
    except (TypeError, ValueError):
        return None, {"status": "invalid_request", "message": f"{field_name} must use YYYY-MM-DD"}


def public_record(record: BaseModel, *, exclude: set[str] | None = None) -> dict[str, Any]:
    return record.model_dump(mode="json", exclude=exclude or {"employee_id"})
