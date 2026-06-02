"""Compatibility shim for Keycloak mock transport."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.keycloak._mock_transport import (
    MockResponse,
    mock_opener,
    mock_settings,
)

__all__ = ["MockResponse", "mock_opener", "mock_settings"]
