"""Tests for the Google Drive adapter."""

from __future__ import annotations

import json
from io import StringIO
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from mcp_docs_toolkit.errors import AUTH_FAILED
from mcp_docs_toolkit.adapters.google_drive.config import GoogleDriveConfig, load_google_drive_config
from mcp_docs_toolkit.adapters.google_drive.mock import GoogleDriveMockDocAdapter
from mcp_docs_toolkit.adapters.google_drive.adapter import GoogleDriveAuthAdapter, GoogleDriveBackendFactory, GoogleDriveDocAdapter
from mcp_docs_toolkit.cli import main
from mcp_docs_toolkit.models import AccessToken


def run_cli(argv, env=None):
    stream = StringIO()
    exit_code = main(argv=argv, env=env or {}, out=stream)
    return exit_code, stream.getvalue()


# Config tests

def test_load_google_drive_config_success():
    env = {"MCP_DOCS_GOOGLE_ACCESS_TOKEN": "ya29.test-token"}
    result = load_google_drive_config(env)
    assert result.ok is True
    assert isinstance(result.config, GoogleDriveConfig)
    assert result.config.access_token == "ya29.test-token"
    assert result.config.api_url == "https://www.googleapis.com/drive/v3"


def test_load_google_drive_config_missing_token():
    result = load_google_drive_config({})
    assert result.ok is False
    assert "MCP_DOCS_GOOGLE_ACCESS_TOKEN" in result.error["message"]


def test_load_google_drive_config_custom_url():
    env = {
        "MCP_DOCS_GOOGLE_ACCESS_TOKEN": "token",
        "MCP_DOCS_GOOGLE_API_URL": "https://custom.drive.api/v3/",
    }
    result = load_google_drive_config(env)
    assert result.ok is True
    assert result.config.api_url == "https://custom.drive.api/v3"


# Auth tests

def test_google_drive_auth_returns_bearer_token():
    config = GoogleDriveConfig(access_token="ya29.test-token")
    auth = GoogleDriveAuthAdapter(config)
    result = auth.authenticate()
    assert result.ok is True
    assert result.token.value == "ya29.test-token"
    assert result.token.token_type == "Bearer"
    assert result.token.principal == "google-drive-user"


# Real adapter fake-transport tests

class FakeResponse:
    def __init__(self, body):
        self._body = body
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


def test_google_drive_list_documents_gets_files_and_normalizes_response(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        parsed = urlparse(request.full_url)
        seen["path"] = parsed.path
        seen["query"] = parse_qs(parsed.query)
        seen["method"] = request.get_method()
        seen["authorization"] = request.get_header("Authorization")
        return FakeResponse(
            json.dumps(
                {
                    "files": [
                        {
                            "id": "file-real-001",
                            "name": "Spec.pdf",
                            "mimeType": "application/pdf",
                            "size": "42",
                            "parents": ["folder-real"],
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("mcp_docs_toolkit.adapters.google_drive.adapter.urlopen", fake_urlopen)

    adapter = GoogleDriveDocAdapter(GoogleDriveConfig(access_token="google-secret"), AccessToken(value="google-secret"))
    result = adapter.list_documents("folder-real")

    assert result.ok is True
    assert seen["path"] == "/drive/v3/files"
    assert seen["method"] == "GET"
    assert seen["authorization"] == "Bearer google-secret"
    assert seen["query"]["pageSize"] == ["100"]
    assert seen["query"]["fields"] == ["files(id,name,mimeType,size,parents)"]
    assert "folder-real" in seen["query"]["q"][0]
    assert result.data["documents"] == [
        {
            "id": "file-real-001",
            "name": "Spec.pdf",
            "folderId": "folder-real",
            "mimeType": "application/pdf",
            "size": 42,
        }
    ]


def test_google_drive_http_401_returns_auth_failed_without_token(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr("mcp_docs_toolkit.adapters.google_drive.adapter.urlopen", fake_urlopen)

    adapter = GoogleDriveDocAdapter(GoogleDriveConfig(access_token="google-secret"), AccessToken(value="google-secret"))
    result = adapter.list_folders()

    assert result.ok is False
    assert result.error.code == AUTH_FAILED
    assert "google-secret" not in result.error.message


# Mock adapter tests

def test_mock_list_folders():
    adapter = GoogleDriveMockDocAdapter()
    result = adapter.list_folders()
    assert result.ok is True
    assert result.data["total"] == 2
    names = [f["name"] for f in result.data["folders"]]
    assert "My Drive" in names
    assert "Shared with me" in names


def test_mock_list_documents():
    adapter = GoogleDriveMockDocAdapter()
    result = adapter.list_documents("folder-001")
    assert result.ok is True
    assert result.data["total"] == 2
    names = [d["name"] for d in result.data["documents"]]
    assert "Quarterly Report.pdf" in names
    assert "Meeting Notes.docx" in names


def test_mock_list_documents_wrong_folder():
    adapter = GoogleDriveMockDocAdapter()
    result = adapter.list_documents("nonexistent")
    assert result.ok is True
    assert result.data["total"] == 0


def test_mock_list_documents_supports_pagination():
    adapter = GoogleDriveMockDocAdapter()

    first_page = adapter.list_documents("folder-001", page_size=1)
    second_page = adapter.list_documents("folder-001", page_cursor=first_page.data["nextCursor"], page_size=1)

    assert first_page.ok is True
    assert first_page.data["total"] == 1
    assert first_page.data["documents"][0]["id"] == "file-001"
    assert first_page.data["nextCursor"] == "1"
    assert second_page.ok is True
    assert second_page.data["total"] == 1
    assert second_page.data["documents"][0]["id"] == "file-002"
    assert "nextCursor" not in second_page.data


def test_mock_download_document():
    adapter = GoogleDriveMockDocAdapter()
    result = adapter.download_document("file-001")
    assert result.ok is True
    assert result.data.filename == "Quarterly Report.pdf"
    assert result.data.content == b"Mock Google Drive file content.\n"


def test_mock_download_not_found():
    adapter = GoogleDriveMockDocAdapter()
    result = adapter.download_document("nonexistent")
    assert result.ok is False
    assert result.error["code"] == "NETWORK_ERROR"


# CLI integration tests

def test_google_drive_mock_list_folders_cli():
    exit_code, text = run_cli(["--backend", "google-drive", "list-folders", "--mock"])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "list_folders"
    assert payload["data"]["total"] == 2


def test_google_drive_mock_list_docs_cli():
    exit_code, text = run_cli(["--backend", "google-drive", "list-docs", "--mock", "--folder", "folder-001"])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["total"] == 2


def test_google_drive_mock_download_cli(tmp_path):
    exit_code, text = run_cli(["--backend", "google-drive", "download", "--mock", "--doc-id", "file-001", "--output", str(tmp_path)])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["filename"] == "Quarterly Report.pdf"
    assert payload["data"]["size"] == 32


# Factory tests

def test_factory_name():
    factory = GoogleDriveBackendFactory()
    assert factory.name == "google-drive"


def test_factory_create_mock_adapter():
    factory = GoogleDriveBackendFactory()
    adapter = factory.create_mock_doc_adapter()
    result = adapter.list_folders()
    assert result.ok is True
