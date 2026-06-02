import json
from urllib.error import HTTPError

from mcp_docs_toolkit.auth import request_access_token
from mcp_docs_toolkit.client import DocumentApiClient
from mcp_docs_toolkit.errors import NETWORK_ERROR
from mcp_docs_toolkit.mock_transport import mock_opener, mock_settings


def test_mock_opener_returns_keycloak_token_without_printing_it():
    result = request_access_token(mock_settings(), opener=mock_opener)

    assert result.ok is True
    assert result.error is None
    assert result.token.value == "mock-access-token"
    assert result.token.principal == "user@example.com"
    assert "mock-access-token" not in repr(result)


def test_mock_opener_lists_public_folders():
    token = request_access_token(mock_settings(), opener=mock_opener).token
    client = DocumentApiClient(mock_settings(), token, opener=mock_opener)

    result = client.list_folders(root_id="ROOT")

    assert result.ok is True
    assert result.data == {
        "folders": [{"id": "F001", "name": "Example Folder", "parentId": None}],
        "total": 1,
    }


def test_mock_opener_lists_public_documents():
    token = request_access_token(mock_settings(), opener=mock_opener).token
    client = DocumentApiClient(mock_settings(), token, opener=mock_opener)

    result = client.list_documents(folder_id="F001")

    assert result.ok is True
    assert result.data == {
        "documents": [
            {
                "id": "D001",
                "name": "Example Document.pdf",
                "folderId": "F001",
                "mimeType": "application/pdf",
                "size": 29,
            }
        ],
        "total": 1,
    }


def test_mock_opener_downloads_public_document_bytes():
    token = request_access_token(mock_settings(), opener=mock_opener).token
    client = DocumentApiClient(mock_settings(), token, opener=mock_opener)

    result = client.download_document(doc_id="D001")

    assert result.ok is True
    assert result.data.filename == "Example Document.pdf"
    assert result.data.content == b"Example mock document bytes.\n"
    assert result.data.mime_type == "application/pdf"


def test_mock_opener_unknown_document_becomes_network_error():
    token = request_access_token(mock_settings(), opener=mock_opener).token
    client = DocumentApiClient(mock_settings(), token, opener=mock_opener)

    result = client.download_document(doc_id="missing")

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert result.error.retryable is True
    assert "HTTP 404" in result.error.message


def test_mock_opener_rejects_bad_password():
    settings = mock_settings(password="wrong-password")

    result = request_access_token(settings, opener=mock_opener)

    assert result.ok is False
    assert result.token is None


def test_mock_opener_http_error_does_not_include_request_body():
    settings = mock_settings(password="wrong-password")

    try:
        mock_opener(type("Request", (), {"full_url": settings.keycloak_url + "/unknown", "data": b"password=wrong"})(), 30)
    except HTTPError as exc:
        rendered = str(exc)
    else:
        rendered = ""

    assert "wrong" not in rendered
    assert "password=" not in rendered
