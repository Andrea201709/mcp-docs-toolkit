"""Compatibility shim for Keycloak environment configuration."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.keycloak._config_compat import (
    REQUIRED_ENV_VARS,
    Settings,
    SettingsResult,
    load_settings,
)

__all__ = ["REQUIRED_ENV_VARS", "Settings", "SettingsResult", "load_settings"]
