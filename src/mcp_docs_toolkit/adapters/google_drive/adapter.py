"""Google Drive backend factory and document adapter."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp_docs_toolkit.adapters.base import AuthAdapter, DocAdapter
from mcp_docs_toolkit.adapters.google_drive.config import GoogleDriveConfig, load_google_drive_config
from mcp_docs_toolkit.adapters.google_drive.mock import GoogleDriveMockDocAdapter
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


class GoogleDriveAuthAdapter:
    """Google Drive uses a pre-obtained OAuth2 access token."""

    def __init__(self, config: GoogleDriveConfig) -> None:
        self._config = config

    def authenticate(self) -> AuthResult:
        return AuthResult(
            ok=True,
            token=AccessToken(
                value=self._config.access_token,
                token_type="Bearer",
                principal="google-drive-user",
            ),
        )


class GoogleDriveDocAdapter:
    """Document operations via the Google Drive API v3."""

    def __init__(self, config: GoogleDriveConfig, token: AccessToken) -> None:
        self._config = config
        self._token = token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token.value}"}

    def _get_json(self, url: str) -> dict[str, object] | ApiResult:
        request = Request(url, headers=self._headers(), method="GET")
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as resp:
                raw = resp.read()
        except HTTPError as exc:
            if exc.code in {401, 403}:
                return ApiResult(ok=False, error=ToolError(code=AUTH_FAILED, message="Google Drive rejected the access token.", retryable=False))
            return _network_error(f"Google Drive API returned HTTP {exc.code}.", (self._token.value,))
        except (TimeoutError, URLError, OSError) as exc:
            return _network_error(str(exc), (self._token.value,))
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError):
            # Some endpoints return raw bytes (e.g. download), not JSON
            return _network_error("Google Drive API response was not valid JSON.", (self._token.value,))
        if not isinstance(body, dict):
            return _network_error("Google Drive API response JSON must be an object.", (self._token.value,))
        return body

    def _get_bytes(self, url: str) -> tuple[bytes, dict[str, str]] | ApiResult:
        request = Request(url, headers=self._headers(), method="GET")
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as resp:
                raw = resp.read()
                headers = dict(resp.headers)
        except HTTPError as exc:
            if exc.code in {401, 403}:
                return ApiResult(ok=False, error=ToolError(code=AUTH_FAILED, message="Google Drive rejected the access token.", retryable=False))
            return _network_error(f"Google Drive API returned HTTP {exc.code}.", (self._token.value,))
        except (TimeoutError, URLError, OSError) as exc:
            return _network_error(str(exc), (self._token.value,))
        return raw, headers

    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        """List Google Drive folders. If root_id given, list children of that folder."""
        base = self._config.api_url
        parent = root_id or "root"
        query = f"'{parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        params = urlencode({"q": query, "fields": "files(id,name,parents)", "pageSize": 100})
        body = self._get_json(f"{base}/files?{params}")
        if isinstance(body, ApiResult):
            return body
        files = body.get("files", [])
        if not isinstance(files, list):
            return _network_error("Google Drive 'files' field must be a list.", (self._token.value,))
        folders = [
            Folder(
                id=str(f.get("id", "")),
                name=str(f.get("name", "")),
                parent_id=str(f.get("parents", [None])[0]) if f.get("parents") else None,
            ).to_dict()
            for f in files
            if isinstance(f, dict)
        ]
        return ApiResult(ok=True, data={"folders": folders, "total": len(folders)})

    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        """List files in a Google Drive folder."""
        base = self._config.api_url
        query = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
        params = urlencode({"q": query, "fields": "files(id,name,mimeType,size,parents)", "pageSize": 100})
        body = self._get_json(f"{base}/files?{params}")
        if isinstance(body, ApiResult):
            return body
        files = body.get("files", [])
        if not isinstance(files, list):
            return _network_error("Google Drive 'files' field must be a list.", (self._token.value,))
        documents = []
        for f in files:
            if not isinstance(f, dict):
                continue
            size_val = f.get("size")
            documents.append(
                Document(
                    id=str(f.get("id", "")),
                    name=str(f.get("name", "")),
                    folder_id=folder_id,
                    mime_type=f.get("mimeType"),
                    size=int(size_val) if size_val else None,
                ).to_dict()
            )
        return ApiResult(ok=True, data={"documents": documents, "total": len(documents)})

    def download_document(self, doc_id: str) -> ApiResult:
        """Download a file from Google Drive."""
        base = self._config.api_url
        # First get file metadata for the name
        meta = self._get_json(f"{base}/files/{doc_id}?fields=name,mimeType")
        if isinstance(meta, ApiResult):
            return meta
        filename = str(meta.get("name", f"{doc_id}.bin"))
        mime_type = str(meta.get("mimeType", "application/octet-stream"))
        # Then download content
        result = self._get_bytes(f"{base}/files/{doc_id}?alt=media")
        if isinstance(result, ApiResult):
            return result
        content, _headers = result
        return ApiResult(
            ok=True,
            data=DownloadedDocument(filename=filename, content=content, mime_type=mime_type),
        )


class GoogleDriveBackendFactory:
    name = "google-drive"
    required_env_vars: Sequence[str] = ("MCP_DOCS_GOOGLE_ACCESS_TOKEN",)

    def load_config(self, env: Mapping[str, str]) -> ConfigResult:
        return load_google_drive_config(env)

    def create_auth(self, config: Any) -> AuthAdapter:
        assert isinstance(config, GoogleDriveConfig)
        return GoogleDriveAuthAdapter(config)

    def create_doc_adapter(self, config: Any, token: AccessToken) -> DocAdapter:
        assert isinstance(config, GoogleDriveConfig)
        return GoogleDriveDocAdapter(config, token)

    def create_mock_doc_adapter(self) -> DocAdapter:
        return GoogleDriveMockDocAdapter()
