"""Keycloak authentication adapter — delegates to the existing auth module."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.keycloak.config import KeycloakConfig
from mcp_docs_toolkit.adapters.keycloak._auth import request_access_token
from mcp_docs_toolkit.adapters.keycloak._config_compat import Settings
from mcp_docs_toolkit.models import AuthResult


class KeycloakAuthAdapter:
    """Wraps the existing Keycloak password-grant authentication."""

    def __init__(self, config: KeycloakConfig) -> None:
        self._config = config

    def _to_settings(self) -> Settings:
        c = self._config
        return Settings(
            keycloak_url=c.keycloak_url,
            keycloak_realm=c.keycloak_realm,
            client_id=c.client_id,
            client_secret=c.client_secret,
            username=c.username,
            password=c.password,
            api_url=c.api_url,
            timeout_seconds=c.timeout_seconds,
        )

    def authenticate(self) -> AuthResult:
        return request_access_token(self._to_settings())
