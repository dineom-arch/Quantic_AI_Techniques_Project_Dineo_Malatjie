"""Process-local identity runtime shared by HTTP and MCP boundaries."""

from app.identity.provider import IdentityProvider
from app.identity.session import SessionStore


identity_provider = IdentityProvider()
session_store = SessionStore(identity_provider)
