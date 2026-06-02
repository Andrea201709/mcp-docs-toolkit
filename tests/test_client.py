import json
from urllib.error import HTTPError, URLError

from mcp_docs_toolkit.client import DocumentApiClient
from mcp_docs_toolkit.config import Settings
from mcp_docs_toolkit.errors import NETWORK_ERROR
from mcp_docs_toolkit.models import AccessToken, DownloadedDocument


class FakeResponse:
    def __init__(self, body, headers=None):
        self._body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        if isinstance(self._body, bytes):
            return self._body
        return json.dumps(self._body).encode("utf-8")


def settings():
    return Settings(
        keycloak_url="https://idp.example.com",
        keycloak_realm="example-realm",
        client_id="docs-cli",
        client_secret="example-secret",
        username="user@example.com",
        password="example-password",
        api_url="https://docs-api.example.com/",
        timeout_seconds=11,
    )


def token():
    return AccessToken(value="token-value", principal="user@example.com")


def token_with_encoded_value():
    return AccessToken(value="tok/en word", principal="user@example.com")


def test_list_folders_posts_generic_payload_and_normalizes_response():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return FakeResponse({"folders": [{"id": "F001", "name": "Example Folder", "parentId": None}]})

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.list_folders(root_id="ROOT")

    assert result.ok is True
    assert result.error is None
    assert result.data == {"folders": [{"id": "F001", "name": "Example Folder", "parentId": None}], "total": 1}
    request, timeout = calls[0]
    assert timeout == 11
    assert request.full_url == "https://docs-api.example.com/folders/list"
    assert request.get_method() == "POST"
    assert request.headers["Authorization"] == "Bearer token-value"
    assert json.loads(request.data.decode("utf-8")) == {"rootFolderId": "ROOT"}


def test_list_documents_posts_folder_and_normalizes_response():
    def opener(request, timeout):
        assert request.full_url == "https://docs-api.example.com/documents/list"
        assert json.loads(request.data.decode("utf-8")) == {"folderId": "F001"}
        return FakeResponse(
            {
                "documents": [
                    {
                        "id": "D001",
                        "name": "Example.pdf",
                        "folderId": "F001",
                        "mimeType": "application/pdf",
                        "size": 123,
                    }
                ]
            }
        )

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.list_documents(folder_id="F001")

    assert result.ok is True
    assert result.data == {
        "documents": [
            {
                "id": "D001",
                "name": "Example.pdf",
                "folderId": "F001",
                "mimeType": "application/pdf",
                "size": 123,
            }
        ],
        "total": 1,
    }


def test_download_document_returns_content_without_leaking_repr():
    def opener(request, timeout):
        assert request.full_url == "https://docs-api.example.com/documents/download"
        assert json.loads(request.data.decode("utf-8")) == {"docId": "D001"}
        return FakeResponse(
            b"file-bytes",
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="Example.pdf"',
            },
        )

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.download_document(doc_id="D001")

    assert result.ok is True
    assert isinstance(result.data, DownloadedDocument)
    assert result.data.filename == "Example.pdf"
    assert result.data.content == b"file-bytes"
    assert result.data.mime_type == "application/pdf"
    assert "file-bytes" not in repr(result.data)


def test_client_http_error_returns_network_error():
    def opener(request, timeout):
        raise HTTPError(request.full_url, 502, "Bad Gateway", hdrs=None, fp=None)

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.list_folders()

    assert result.ok is False
    assert result.data is None
    assert result.error.code == NETWORK_ERROR
    assert result.error.retryable is True
    assert "HTTP 502" in result.error.message


def test_client_invalid_json_returns_network_error():
    def opener(request, timeout):
        return FakeResponse(b"not json")

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.list_documents(folder_id="F001")

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert "valid JSON" in result.error.message


def test_list_folders_rejects_invalid_folder_shape():
    def opener(request, timeout):
        return FakeResponse({"folders": None})

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.list_folders()

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert "folders" in result.error.message
    assert "list" in result.error.message


def test_list_documents_rejects_invalid_document_shape():
    def opener(request, timeout):
        return FakeResponse({"documents": None})

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.list_documents(folder_id="F001")

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert "documents" in result.error.message
    assert "list" in result.error.message


def test_client_url_error_returns_network_error():
    def opener(request, timeout):
        raise URLError("connection refused")

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.download_document(doc_id="D001")

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert result.error.retryable is True
    assert "connection refused" in result.error.message


def test_client_url_error_redacts_access_token():
    def opener(request, timeout):
        raise URLError("Bearer token-value connection refused")

    client = DocumentApiClient(settings(), token(), opener=opener)
    result = client.download_document(doc_id="D001")

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert "token-value" not in result.error.message
    assert "connection refused" in result.error.message


def test_client_url_error_redacts_encoded_access_token():
    def opener(request, timeout):
        raise URLError("Bearer tok%2Fen+word connection refused")

    client = DocumentApiClient(settings(), token_with_encoded_value(), opener=opener)
    result = client.download_document(doc_id="D001")

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert "tok/en word" not in result.error.message
    assert "tok%2Fen+word" not in result.error.message
    assert "connection refused" in result.error.message
