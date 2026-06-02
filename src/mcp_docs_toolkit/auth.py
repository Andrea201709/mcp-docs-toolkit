"""Compatibility shim for Keycloak authentication helpers."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.keycloak._auth import (
    Opener,
    ResponseLike,
    request_access_token,
)

__all__ = ["Opener", "ResponseLike", "request_access_token"]
