"""Keycloak backend configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from mcp_docs_toolkit.errors import CONFIG_INVALID, CONFIG_MISSING
from mcp_docs_toolkit.models import ConfigResult

REQUIRED_ENV_VARS = (
    "MCP_DOCS_KEYCLOAK_URL",
    "MCP_DOCS_KEYCLOAK_REALM",
    "MCP_DOCS_CLIENT_ID",
    "MCP_DOCS_CLIENT_SECRET",
    "MCP_DOCS_USERNAME",
    "MCP_DOCS_PASSWORD",
    "MCP_DOCS_API_URL",
)


@dataclass(frozen=True)
class KeycloakConfig:
    keycloak_url: str
    keycloak_realm: str
    client_id: str
    client_secret: str = field(repr=False)
    username: str
    password: str = field(repr=False)
    api_url: str
    timeout_seconds: int = 30


def _parse_timeout(raw: str | None) -> tuple[int | None, dict[str, object] | None]:
    if raw is None or raw == "":
        return 30, None
    try:
        value = int(raw)
    except ValueError:
        return None, {
            "code": CONFIG_INVALID,
            "message": "MCP_DOCS_TIMEOUT_SECONDS must be an integer greater than 0.",
            "retryable": False,
        }
    if value <= 0:
        return None, {
            "code": CONFIG_INVALID,
            "message": "MCP_DOCS_TIMEOUT_SECONDS must be an integer greater than 0.",
            "retryable": False,
        }
    return value, None


def load_keycloak_config(env: Mapping[str, str]) -> ConfigResult:
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

    timeout_seconds, timeout_error = _parse_timeout(env.get("MCP_DOCS_TIMEOUT_SECONDS"))
    if timeout_error is not None:
        return ConfigResult(ok=False, error=timeout_error)

    config = KeycloakConfig(
        keycloak_url=env["MCP_DOCS_KEYCLOAK_URL"].rstrip("/"),
        keycloak_realm=env["MCP_DOCS_KEYCLOAK_REALM"],
        client_id=env["MCP_DOCS_CLIENT_ID"],
        client_secret=env["MCP_DOCS_CLIENT_SECRET"],
        username=env["MCP_DOCS_USERNAME"],
        password=env["MCP_DOCS_PASSWORD"],
        api_url=env["MCP_DOCS_API_URL"].rstrip("/"),
        timeout_seconds=timeout_seconds or 30,
    )
    return ConfigResult(ok=True, config=config)
