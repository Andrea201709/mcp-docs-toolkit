"""Notion backend factory and document adapter."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mcp_docs_toolkit.adapters.base import AuthAdapter, DocAdapter
from mcp_docs_toolkit.adapters.notion.config import NotionConfig, load_notion_config
from mcp_docs_toolkit.adapters.notion.mock import NotionMockDocAdapter
from mcp_docs_toolkit.errors import AUTH_FAILED, NETWORK_ERROR
from mcp_docs_toolkit.models import (
    AccessToken,
    ApiResult,
    AuthResult,
    ConfigResult,
    Document,
    Folder,
    ToolError,
)
from mcp_docs_toolkit.redaction import redact_values


def _network_error(message: str, sensitive: tuple[str, ...] = ()) -> ApiResult:
    return ApiResult(ok=False, error=ToolError(code=NETWORK_ERROR, message=redact_values(message, sensitive), retryable=True))


class NotionAuthAdapter:
    """Notion uses a static integration token — no OAuth flow."""

    def __init__(self, config: NotionConfig) -> None:
        self._config = config

    def authenticate(self) -> AuthResult:
        return AuthResult(
            ok=True,
            token=AccessToken(
                value=self._config.token,
                token_type="Bearer",
                principal="notion-user",
            ),
        )


class NotionDocAdapter:
    """Document operations via the Notion API."""

    def __init__(self, config: NotionConfig, token: AccessToken) -> None:
        self._config = config
        self._token = token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token.value}",
            "Notion-Version": self._config.version,
            "Content-Type": "application/json",
        }

    def _get_json(self, url: str) -> dict[str, object] | ApiResult:
        request = Request(url, headers=self._headers(), method="GET")
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as resp:
                raw = resp.read()
        except HTTPError as exc:
            if exc.code in {401, 403}:
                return ApiResult(ok=False, error=ToolError(code=AUTH_FAILED, message="Notion rejected the API token.", retryable=False))
            return _network_error(f"Notion API returned HTTP {exc.code}.", (self._token.value,))
        except (TimeoutError, URLError, OSError) as exc:
            return _network_error(str(exc), (self._token.value,))
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError):
            return _network_error("Notion API response was not valid JSON.", (self._token.value,))
        if not isinstance(body, dict):
            return _network_error("Notion API response JSON must be an object.", (self._token.value,))
        return body

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object] | ApiResult:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as resp:
                raw = resp.read()
        except HTTPError as exc:
            if exc.code in {401, 403}:
                return ApiResult(ok=False, error=ToolError(code=AUTH_FAILED, message="Notion rejected the API token.", retryable=False))
            return _network_error(f"Notion API returned HTTP {exc.code}.", (self._token.value,))
        except (TimeoutError, URLError, OSError) as exc:
            return _network_error(str(exc), (self._token.value,))
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError):
            return _network_error("Notion API response was not valid JSON.", (self._token.value,))
        if not isinstance(body, dict):
            return _network_error("Notion API response JSON must be an object.", (self._token.value,))
        return body

    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        """List Notion pages/databases (treated as 'folders')."""
        base = self._config.api_url
        payload: dict[str, object] = {"page_size": 100}
        if root_id:
            payload["filter"] = {"value": "page", "property": "object"}
        body = self._post_json(f"{base}/v1/search", payload)
        if isinstance(body, ApiResult):
            return body
        results = body.get("results", [])
        if not isinstance(results, list):
            return _network_error("Notion search results must be a list.", (self._token.value,))
        folders = []
        for item in results:
            if not isinstance(item, dict):
                continue
            obj_id = item.get("id", "")
            obj_type = item.get("object", "")
            title = ""
            properties = item.get("properties", {})
            if isinstance(properties, dict):
                for prop in properties.values():
                    if isinstance(prop, dict) and prop.get("type") == "title":
                        title_arr = prop.get("title", [])
                        if isinstance(title_arr, list) and title_arr:
                            title = title_arr[0].get("plain_text", "") if isinstance(title_arr[0], dict) else ""
                        break
            if not title:
                title = f"{obj_type}-{obj_id[:8]}"
            parent = item.get("parent", {})
            parent_id = parent.get("page_id") or parent.get("database_id") or parent.get("workspace") or None
            folders.append(Folder(id=str(obj_id), name=str(title), parent_id=str(parent_id) if parent_id else None).to_dict())
        return ApiResult(ok=True, data={"folders": folders, "total": len(folders)})

    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        """List child blocks/pages within a Notion page (treated as 'documents')."""
        base = self._config.api_url
        body = self._get_json(f"{base}/v1/blocks/{folder_id}/children?page_size=100")
        if isinstance(body, ApiResult):
            return body
        results = body.get("results", [])
        if not isinstance(results, list):
            return _network_error("Notion blocks results must be a list.", (self._token.value,))
        documents = []
        for item in results:
            if not isinstance(item, dict):
                continue
            block_id = str(item.get("id", ""))
            block_type = str(item.get("type", "unknown"))
            text_content = ""
            type_data = item.get(block_type, {})
            if isinstance(type_data, dict):
                rich_text = type_data.get("rich_text", [])
                if isinstance(rich_text, list):
                    text_content = "".join(
                        rt.get("plain_text", "") for rt in rich_text if isinstance(rt, dict)
                    )
            name = text_content[:80].strip() or f"{block_type}-{block_id[:8]}"
            documents.append(
                Document(
                    id=block_id,
                    name=name,
                    folder_id=folder_id,
                    mime_type="text/plain" if block_type == "paragraph" else f"notion/{block_type}",
                    size=len(text_content.encode("utf-8")) if text_content else None,
                ).to_dict()
            )
        return ApiResult(ok=True, data={"documents": documents, "total": len(documents)})

    def download_document(self, doc_id: str) -> ApiResult:
        """Get a single Notion block and return its content."""
        base = self._config.api_url
        body = self._get_json(f"{base}/v1/blocks/{doc_id}")
        if isinstance(body, ApiResult):
            return body
        block_type = str(body.get("type", "unknown"))
        text_content = ""
        type_data = body.get(block_type, {})
        if isinstance(type_data, dict):
            rich_text = type_data.get("rich_text", [])
            if isinstance(rich_text, list):
                text_content = "".join(
                    rt.get("plain_text", "") for rt in rich_text if isinstance(rt, dict)
                )
        content = text_content.encode("utf-8") or f"Notion block {doc_id} ({block_type})".encode("utf-8")
        from mcp_docs_toolkit.models import DownloadedDocument

        return ApiResult(
            ok=True,
            data=DownloadedDocument(
                filename=f"{doc_id}.txt",
                content=content,
                mime_type="text/plain",
            ),
        )


class NotionBackendFactory:
    name = "notion"
    required_env_vars: Sequence[str] = ("MCP_DOCS_NOTION_TOKEN",)

    def load_config(self, env: Mapping[str, str]) -> ConfigResult:
        return load_notion_config(env)

    def create_auth(self, config: Any) -> AuthAdapter:
        assert isinstance(config, NotionConfig)
        return NotionAuthAdapter(config)

    def create_doc_adapter(self, config: Any, token: AccessToken) -> DocAdapter:
        assert isinstance(config, NotionConfig)
        return NotionDocAdapter(config, token)

    def create_mock_doc_adapter(self) -> DocAdapter:
        return NotionMockDocAdapter()
