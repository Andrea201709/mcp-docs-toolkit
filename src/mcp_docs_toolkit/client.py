"""Compatibility shim for the Keycloak document API client."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.keycloak._client import (
    DocumentApiClient,
    Opener,
    ResponseLike,
)

__all__ = ["DocumentApiClient", "Opener", "ResponseLike"]
