"""Deterministic access to repository-local MCP runtime modules.

The repository's controlled top-level ``mcp/`` directory intentionally is
not a Python package, leaving the ``mcp`` package name to the official SDK.
This adapter loads the local server and client under private, non-conflicting
module names derived from this file's repository location.
"""

from __future__ import annotations

from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MCP_DIRECTORY = REPOSITORY_ROOT / "mcp"


def _load_local_module(module_name: str, filename: str) -> ModuleType:
    path = LOCAL_MCP_DIRECTORY / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Unable to load local MCP module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


@lru_cache(maxsize=1)
def local_server_module() -> ModuleType:
    return _load_local_module("_meridian_compass_mcp_server", "server.py")


@lru_cache(maxsize=1)
def local_client_module() -> ModuleType:
    return _load_local_module("_meridian_compass_mcp_client", "client.py")


def create_mcp_server() -> tuple[Any, Any]:
    """Create the local Meridian MCP server through the shared runtime path."""

    return local_server_module().create_mcp_server()


def meridian_mcp_client_class() -> type[Any]:
    """Expose the local client class without claiming the SDK namespace."""

    return local_client_module().MeridianMCPClient

