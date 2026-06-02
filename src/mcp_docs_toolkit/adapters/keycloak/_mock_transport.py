"""In-process mock transport for credential-free demos and tests."""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.parse import parse_qs
from urllib.request import Request

from mcp_docs_toolkit.adapters.keycloak._config_compat import Settings
from mcp_docs_toolkit.mock_data import (
    MOCK_ACCESS_TOKEN,
    MOCK_BASE_URL,
    MOCK_CLIENT_ID,
    MOCK_CLIENT_SECRET,
    MOCK_DOCUMENT_CONTENT,
    MOCK_DOCUMENTS,
    MOCK_FOLDERS,
    MOCK_PASSWORD,
    MOCK_REALM,
    MOCK_USERNAME,
)


class MockResponse:
    def __init__(self, body: bytes | dict[str, object], headers: dict[str, str] | None = None):
        self._body = body
        self.headers = headers or {}

    def __enter__(self) -> "MockResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        if isinstance(self._body, bytes):
            return self._body
        return json.dumps(self._body).encode("utf-8")


def mock_settings(password: str = MOCK_PASSWORD) -> Settings:
    return Settings(
        keycloak_url=MOCK_BASE_URL,
        keycloak_realm=MOCK_REALM,
        client_id=MOCK_CLIENT_ID,
        client_secret=MOCK_CLIENT_SECRET,
        username=MOCK_USERNAME,
        password=password,
        api_url=MOCK_BASE_URL,
        timeout_seconds=3,
    )


def _raise_http_error(url: str, code: int, reason: str) -> None:
    raise HTTPError(url, code, reason, hdrs=None, fp=None)


def _request_payload(request: Request) -> dict[str, object]:
    if request.data is None:
        return {}
    try:
        return json.loads(request.data.decode("utf-8"))
    except json.JSONDecodeError:
        return {key: values[0] for key, values in parse_qs(request.data.decode("utf-8")).items()}


def _token_response(request: Request) -> MockResponse:
    form = _request_payload(request)
    if (
        form.get("client_id") != MOCK_CLIENT_ID
        or form.get("client_secret") != MOCK_CLIENT_SECRET
        or form.get("username") != MOCK_USERNAME
        or form.get("password") != MOCK_PASSWORD
    ):
        _raise_http_error(request.full_url, 401, "Unauthorized")
    return MockResponse(
        {
            "access_token": MOCK_ACCESS_TOKEN,
            "expires_in": 300,
            "token_type": "Bearer",
        }
    )


def _require_token(request: Request) -> None:
    if request.headers.get("Authorization") != f"Bearer {MOCK_ACCESS_TOKEN}":
        _raise_http_error(request.full_url, 401, "Unauthorized")


def _folders_response(request: Request) -> MockResponse:
    _require_token(request)
    payload = _request_payload(request)
    root_id = payload.get("rootFolderId")
    folders = MOCK_FOLDERS if root_id in (None, "", "ROOT") else []
    return MockResponse({"folders": folders})


def _documents_response(request: Request) -> MockResponse:
    _require_token(request)
    payload = _request_payload(request)
    folder_id = payload.get("folderId")
    documents = [document for document in MOCK_DOCUMENTS if document["folderId"] == folder_id]
    return MockResponse({"documents": documents})


def _download_response(request: Request) -> MockResponse:
    _require_token(request)
    payload = _request_payload(request)
    doc_id = payload.get("docId")
    document = next((item for item in MOCK_DOCUMENTS if item["id"] == doc_id), None)
    if document is None:
        _raise_http_error(request.full_url, 404, "Not Found")
    return MockResponse(
        MOCK_DOCUMENT_CONTENT,
        headers={
            "Content-Type": str(document["mimeType"]),
            "Content-Disposition": f'attachment; filename="{document["name"]}"',
        },
    )


def mock_opener(request: Request, timeout: int) -> MockResponse:
    if request.full_url.endswith(f"/realms/{MOCK_REALM}/protocol/openid-connect/token"):
        return _token_response(request)
    if request.full_url.endswith("/folders/list"):
        return _folders_response(request)
    if request.full_url.endswith("/documents/list"):
        return _documents_response(request)
    if request.full_url.endswith("/documents/download"):
        return _download_response(request)
    _raise_http_error(request.full_url, 404, "Not Found")
