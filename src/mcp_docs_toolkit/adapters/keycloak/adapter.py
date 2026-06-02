"""Keycloak backend factory and document adapter."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mcp_docs_toolkit.adapters.base import AuthAdapter, DocAdapter
from mcp_docs_toolkit.adapters.keycloak.auth import KeycloakAuthAdapter
from mcp_docs_toolkit.adapters.keycloak.config import KeycloakConfig, load_keycloak_config
from mcp_docs_toolkit.adapters.keycloak.mock import KeycloakMockDocAdapter
from mcp_docs_toolkit.adapters.keycloak._client import DocumentApiClient
from mcp_docs_toolkit.adapters.keycloak._config_compat import Settings
from mcp_docs_toolkit.models import AccessToken, ApiResult, ConfigResult


class KeycloakDocAdapter:
    """Delegates to the existing DocumentApiClient."""

    def __init__(self, config: KeycloakConfig, token: AccessToken) -> None:
        settings = Settings(
            keycloak_url=config.keycloak_url,
            keycloak_realm=config.keycloak_realm,
            client_id=config.client_id,
            client_secret=config.client_secret,
            username=config.username,
            password=config.password,
            api_url=config.api_url,
            timeout_seconds=config.timeout_seconds,
        )
        self._client = DocumentApiClient(settings, token)

    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        return self._client.list_folders(root_id=root_id)

    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        return self._client.list_documents(folder_id=folder_id)

    def download_document(self, doc_id: str) -> ApiResult:
        return self._client.download_document(doc_id=doc_id)


class KeycloakBackendFactory:
    name = "keycloak"
    required_env_vars: Sequence[str] = (
        "MCP_DOCS_KEYCLOAK_URL",
        "MCP_DOCS_KEYCLOAK_REALM",
        "MCP_DOCS_CLIENT_ID",
        "MCP_DOCS_CLIENT_SECRET",
        "MCP_DOCS_USERNAME",
        "MCP_DOCS_PASSWORD",
        "MCP_DOCS_API_URL",
    )

    def load_config(self, env: Mapping[str, str]) -> ConfigResult:
        return load_keycloak_config(env)

    def create_auth(self, config: Any) -> AuthAdapter:
        assert isinstance(config, KeycloakConfig)
        return KeycloakAuthAdapter(config)

    def create_doc_adapter(self, config: Any, token: AccessToken) -> DocAdapter:
        assert isinstance(config, KeycloakConfig)
        return KeycloakDocAdapter(config, token)

    def create_mock_doc_adapter(self) -> DocAdapter:
        return KeycloakMockDocAdapter()
