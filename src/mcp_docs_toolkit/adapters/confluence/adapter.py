"""Confluence backend factory and document adapter."""

from __future__ import annotations

import base64
import json
from json import JSONDecodeError
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mcp_docs_toolkit.adapters.base import AuthAdapter, DocAdapter
from mcp_docs_toolkit.adapters.confluence.config import ConfluenceConfig, load_confluence_config
from mcp_docs_toolkit.adapters.confluence.mock import ConfluenceMockDocAdapter
from mcp_docs_toolkit.errors import AUTH_FAILED, NETWORK_ERROR
from mcp_docs_toolkit.models import (
    AccessToken,
    ApiResult,
    AuthResult,
    ConfigResult,
    Document,
    DownloadedDocument,
    Folder,
    ToolError,
)
from mcp_docs_toolkit.redaction import redact_values


def _network_error(message: str, sensitive: tuple[str, ...] = ()) -> ApiResult:
    return ApiResult(ok=False, error=ToolError(code=NETWORK_ERROR, message=redact_values(message, sensitive), retryable=True))


class ConfluenceAuthAdapter:
    """Confluence uses Basic Auth (email:api_token)."""

    def __init__(self, config: ConfluenceConfig) -> None:
        self._config = config

    def authenticate(self) -> AuthResult:
        credentials = base64.b64encode(
            f"{self._config.email}:{self._config.api_token}".encode("utf-8")
        ).decode("ascii")
        return AuthResult(
            ok=True,
            token=AccessToken(
                value=credentials,
                token_type="Basic",
                principal=self._config.email,
            ),
        )


class ConfluenceDocAdapter:
    """Document operations via the Confluence REST API v2."""

    def __init__(self, config: ConfluenceConfig, token: AccessToken) -> None:
        self._config = config
        self._token = token

    def _api_base(self) -> str:
        return f"{self._config.base_url}/rest/api"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Basic {self._token.value}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get_json(self, url: str) -> dict[str, object] | ApiResult:
        request = Request(url, headers=self._headers(), method="GET")
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as resp:
                raw = resp.read()
        except HTTPError as exc:
            if exc.code in {401, 403}:
                return ApiResult(ok=False, error=ToolError(code=AUTH_FAILED, message="Confluence rejected the credentials.", retryable=False))
            return _network_error(f"Confluence API returned HTTP {exc.code}.", (self._token.value,))
        except (TimeoutError, URLError, OSError) as exc:
            return _network_error(str(exc), (self._token.value,))
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError):
            return _network_error("Confluence API response was not valid JSON.", (self._token.value,))
        if not isinstance(body, dict):
            return _network_error("Confluence API response JSON must be an object.", (self._token.value,))
        return body

    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        """List Confluence spaces (or child pages if root_id given)."""
        base = self._api_base()
        if root_id:
            body = self._get_json(f"{base}/v2/pages/{root_id}/children?limit=100")
        else:
            body = self._get_json(f"{base}/v2/spaces?limit=100")
        if isinstance(body, ApiResult):
            return body
        results = body.get("results", [])
        if not isinstance(results, list):
            return _network_error("Confluence response 'results' must be a list.", (self._token.value,))
        folders = []
        for item in results:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", ""))
            title = str(item.get("title", "") or item.get("name", f"item-{item_id[:8]}"))
            parent = item.get("parent_id") or item.get("parentId") or item.get("spaceId")
            folders.append(Folder(id=item_id, name=title, parent_id=str(parent) if parent else None).to_dict())
        return ApiResult(ok=True, data={"folders": folders, "total": len(folders)})

    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        """List pages in a Confluence space or as children of a page."""
        base = self._api_base()
        body = self._get_json(f"{base}/v2/pages?space-id={folder_id}&limit=100")
        if isinstance(body, ApiResult):
            # If space-id lookup fails, try as parent page
            body = self._get_json(f"{base}/v2/pages/{folder_id}/children?limit=100")
            if isinstance(body, ApiResult):
                return body
        results = body.get("results", [])
        if not isinstance(results, list):
            return _network_error("Confluence response 'results' must be a list.", (self._token.value,))
        documents = []
        for item in results:
            if not isinstance(item, dict):
                continue
            page_id = str(item.get("id", ""))
            title = str(item.get("title", f"page-{page_id[:8]}"))
            body_data = item.get("body", {})
            body_size = len(json.dumps(body_data).encode("utf-8")) if isinstance(body_data, dict) else 0
            documents.append(
                Document(
                    id=page_id,
                    name=title,
                    folder_id=folder_id,
                    mime_type="text/html",
                    size=body_size,
                ).to_dict()
            )
        return ApiResult(ok=True, data={"documents": documents, "total": len(documents)})

    def download_document(self, doc_id: str) -> ApiResult:
        """Get a Confluence page with its body content."""
        base = self._api_base()
        body = self._get_json(f"{base}/v2/pages/{doc_id}?body-format=storage")
        if isinstance(body, ApiResult):
            return body
        title = str(body.get("title", f"page-{doc_id}"))
        body_data = body.get("body", {})
        storage = {}
        if isinstance(body_data, dict):
            storage = body_data.get("storage", {})
        html_content = storage.get("value", "") if isinstance(storage, dict) else ""
        content = html_content.encode("utf-8") or f"<h1>{title}</h1>".encode("utf-8")
        return ApiResult(
            ok=True,
            data=DownloadedDocument(
                filename=f"{title}.html",
                content=content,
                mime_type="text/html",
            ),
        )


class ConfluenceBackendFactory:
    name = "confluence"
    required_env_vars: Sequence[str] = (
        "MCP_DOCS_CONFLUENCE_URL",
        "MCP_DOCS_CONFLUENCE_EMAIL",
        "MCP_DOCS_CONFLUENCE_API_TOKEN",
    )

    def load_config(self, env: Mapping[str, str]) -> ConfigResult:
        return load_confluence_config(env)

    def create_auth(self, config: Any) -> AuthAdapter:
        assert isinstance(config, ConfluenceConfig)
        return ConfluenceAuthAdapter(config)

    def create_doc_adapter(self, config: Any, token: AccessToken) -> DocAdapter:
        assert isinstance(config, ConfluenceConfig)
        return ConfluenceDocAdapter(config, token)

    def create_mock_doc_adapter(self) -> DocAdapter:
        return ConfluenceMockDocAdapter()
