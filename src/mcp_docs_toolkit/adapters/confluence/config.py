"""Confluence backend configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from mcp_docs_toolkit.errors import CONFIG_MISSING
from mcp_docs_toolkit.models import ConfigResult

REQUIRED_ENV_VARS = (
    "MCP_DOCS_CONFLUENCE_URL",
    "MCP_DOCS_CONFLUENCE_EMAIL",
    "MCP_DOCS_CONFLUENCE_API_TOKEN",
)


@dataclass(frozen=True)
class ConfluenceConfig:
    base_url: str
    email: str
    api_token: str = field(repr=False)
    timeout_seconds: int = 30


def load_confluence_config(env: Mapping[str, str]) -> ConfigResult:
    missing = tuple(name for name in REQUIRED_ENV_VARS if not env.get(name))
    if missing:
        return ConfigResult(
            ok=False,
            error={
                "code": CONFIG_MISSING,
                "message": "Missing required environment variables: " + ", ".join(missing),
                "retryable": False,
            },
        )
    config = ConfluenceConfig(
        base_url=env["MCP_DOCS_CONFLUENCE_URL"].rstrip("/"),
        email=env["MCP_DOCS_CONFLUENCE_EMAIL"],
        api_token=env["MCP_DOCS_CONFLUENCE_API_TOKEN"],
        timeout_seconds=int(env.get("MCP_DOCS_CONFLUENCE_TIMEOUT", "30") or "30"),
    )
    return ConfigResult(ok=True, config=config)
