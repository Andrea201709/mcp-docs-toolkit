"""Google Drive backend configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from mcp_docs_toolkit.errors import CONFIG_MISSING
from mcp_docs_toolkit.models import ConfigResult

REQUIRED_ENV_VARS = ("MCP_DOCS_GOOGLE_ACCESS_TOKEN",)


@dataclass(frozen=True)
class GoogleDriveConfig:
    access_token: str = field(repr=False)
    api_url: str = "https://www.googleapis.com/drive/v3"
    timeout_seconds: int = 30


def load_google_drive_config(env: Mapping[str, str]) -> ConfigResult:
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
    config = GoogleDriveConfig(
        access_token=env["MCP_DOCS_GOOGLE_ACCESS_TOKEN"],
        api_url=env.get("MCP_DOCS_GOOGLE_API_URL", "https://www.googleapis.com/drive/v3").rstrip("/"),
        timeout_seconds=int(env.get("MCP_DOCS_GOOGLE_TIMEOUT", "30") or "30"),
    )
    return ConfigResult(ok=True, config=config)
