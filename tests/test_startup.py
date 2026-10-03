from fastapi import FastAPI

from app.main import app


def test_application_imports() -> None:
    assert isinstance(app, FastAPI)
    assert app.title == "Meridian Compass"


def test_canonical_routes_are_registered() -> None:
    api_paths = set(app.openapi()["paths"])
    mount_paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/health" in api_paths
    assert "/chat" in api_paths
    assert "/auth/identities" in api_paths
    assert "/auth/session" in api_paths
    assert "/mcp" in mount_paths

