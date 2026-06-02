"""Generic document API client."""

from __future__ import annotations

import json
import re
from json import JSONDecodeError
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mcp_docs_toolkit.adapters.keycloak._config_compat import Settings
from mcp_docs_toolkit.errors import NETWORK_ERROR
from mcp_docs_toolkit.models import AccessToken, ApiResult, Document, DownloadedDocument, Folder, ToolError
from mcp_docs_toolkit.redaction import redact_values


class ResponseLike(Protocol):
    headers: object

    def __enter__(self) -> "ResponseLike": ...

    def __exit__(self, exc_type, exc, tb) -> bool: ...

    def read(self) -> bytes: ...


Opener = Callable[..., ResponseLike]


def _network_error(message: str, sensitive_values: tuple[str, ...] = ()) -> ApiResult:
    return ApiResult(
        ok=False,
        error=ToolError(code=NETWORK_ERROR, message=redact_values(message, sensitive_values), retryable=True),
    )


def _header_value(headers: object, name: str) -> str | None:
    if hasattr(headers, "get"):
        value = headers.get(name)  # type: ignore[attr-defined]
        return str(value) if value is not None else None
    return None


def _filename_from_disposition(disposition: str | None, fallback: str) -> str:
    if not disposition:
        return fallback
    match = re.search(r'filename="?([^";]+)"?', disposition)
    return match.group(1) if match else fallback


def _require_list_field(body: dict[str, object], field_name: str) -> list[object] | ApiResult:
    value = body.get(field_name, [])
    if not isinstance(value, list):
        return _network_error(f"Document API response field {field_name} must be a list.")
    return value


class DocumentApiClient:
    def __init__(self, settings: Settings, token: AccessToken, opener: Opener = urlopen):
        self.settings = settings
        self.token = token
        self.opener = opener

    def _url(self, path: str) -> str:
        return f"{self.settings.api_url.rstrip('/')}/{path.lstrip('/')}"

    def _request(self, path: str, payload: dict[str, object]) -> tuple[bytes, object] | ApiResult:
        request = Request(
            self._url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"{self.token.token_type} {self.token.value}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.settings.timeout_seconds) as response:
                return response.read(), response.headers
        except HTTPError as exc:
            return _network_error(f"Document API returned HTTP {exc.code}.")
        except (TimeoutError, URLError, OSError) as exc:
            return _network_error(str(exc), (self.token.value,))

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object] | ApiResult:
        response = self._request(path, payload)
        if isinstance(response, ApiResult):
            return response
        raw_body, _headers = response
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError):
            return _network_error("Document API response was not valid JSON.")
        if not isinstance(body, dict):
            return _network_error("Document API response JSON must be an object.")
        return body

    def list_folders(self, root_id: str | None = None) -> ApiResult:
        payload = {"rootFolderId": root_id} if root_id else {}
        body = self._post_json("/folders/list", payload)
        if isinstance(body, ApiResult):
            return body
        raw_folders = _require_list_field(body, "folders")
        if isinstance(raw_folders, ApiResult):
            return raw_folders
        folders = [
            Folder(id=str(item.get("id", "")), name=str(item.get("name", "")), parent_id=item.get("parentId")).to_dict()
            for item in raw_folders
            if isinstance(item, dict)
        ]
        return ApiResult(ok=True, data={"folders": folders, "total": len(folders)})

    def list_documents(self, folder_id: str) -> ApiResult:
        body = self._post_json("/documents/list", {"folderId": folder_id})
        if isinstance(body, ApiResult):
            return body
        raw_documents = _require_list_field(body, "documents")
        if isinstance(raw_documents, ApiResult):
            return raw_documents
        documents = [
            Document(
                id=str(item.get("id", "")),
                name=str(item.get("name", "")),
                folder_id=str(item.get("folderId", folder_id)),
                mime_type=item.get("mimeType"),
                size=item.get("size"),
            ).to_dict()
            for item in raw_documents
            if isinstance(item, dict)
        ]
        return ApiResult(ok=True, data={"documents": documents, "total": len(documents)})

    def download_document(self, doc_id: str) -> ApiResult:
        response = self._request("/documents/download", {"docId": doc_id})
        if isinstance(response, ApiResult):
            return response
        content, headers = response
        mime_type = _header_value(headers, "Content-Type")
        filename = _filename_from_disposition(_header_value(headers, "Content-Disposition"), f"{doc_id}.bin")
        return ApiResult(ok=True, data=DownloadedDocument(filename=filename, content=content, mime_type=mime_type))
