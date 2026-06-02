"""Tests for the Notion adapter."""

from __future__ import annotations

import json
from io import StringIO
from urllib.error import HTTPError

from mcp_docs_toolkit.errors import AUTH_FAILED
from mcp_docs_toolkit.adapters.notion.config import NotionConfig, load_notion_config
from mcp_docs_toolkit.adapters.notion.mock import NotionMockDocAdapter
from mcp_docs_toolkit.adapters.notion.adapter import NotionAuthAdapter, NotionBackendFactory, NotionDocAdapter
from mcp_docs_toolkit.cli import main
from mcp_docs_toolkit.models import AccessToken


def run_cli(argv, env=None):
    stream = StringIO()
    exit_code = main(argv=argv, env=env or {}, out=stream)
    return exit_code, stream.getvalue()


# Config tests

def test_load_notion_config_success():
    env = {"MCP_DOCS_NOTION_TOKEN": "secret-token"}
    result = load_notion_config(env)
    assert result.ok is True
    assert isinstance(result.config, NotionConfig)
    assert result.config.token == "secret-token"
    assert result.config.api_url == "https://api.notion.com"
    assert result.config.version == "2022-06-28"


def test_load_notion_config_missing_token():
    result = load_notion_config({})
    assert result.ok is False
    assert "MCP_DOCS_NOTION_TOKEN" in result.error["message"]


def test_load_notion_config_custom_api_url():
    env = {"MCP_DOCS_NOTION_TOKEN": "t", "MCP_DOCS_NOTION_API_URL": "https://custom.api.com/"}
    result = load_notion_config(env)
    assert result.ok is True
    assert result.config.api_url == "https://custom.api.com"


# Auth tests

def test_notion_auth_returns_bearer_token():
    config = NotionConfig(token="test-token")
    auth = NotionAuthAdapter(config)
    result = auth.authenticate()
    assert result.ok is True
    assert result.token.value == "test-token"
    assert result.token.token_type == "Bearer"
    assert result.token.principal == "notion-user"


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


def test_notion_list_folders_posts_search_request_and_normalizes_response(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["authorization"] = request.get_header("Authorization")
        seen["notion_version"] = request.get_header("Notion-version")
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            json.dumps(
                {
                    "results": [
                        {
                            "id": "page-real-001",
                            "object": "page",
                            "properties": {"Name": {"type": "title", "title": [{"plain_text": "Real Project"}]}},
                            "parent": {"workspace": True},
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("mcp_docs_toolkit.adapters.notion.adapter.urlopen", fake_urlopen)

    adapter = NotionDocAdapter(NotionConfig(token="notion-secret"), AccessToken(value="notion-secret"))
    result = adapter.list_folders()

    assert result.ok is True
    assert seen["url"] == "https://api.notion.com/v1/search"
    assert seen["method"] == "POST"
    assert seen["authorization"] == "Bearer notion-secret"
    assert seen["notion_version"] == "2022-06-28"
    assert seen["payload"] == {"page_size": 100}
    assert result.data["folders"] == [{"id": "page-real-001", "name": "Real Project", "parentId": "True"}]


def test_notion_http_401_returns_auth_failed_without_token(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr("mcp_docs_toolkit.adapters.notion.adapter.urlopen", fake_urlopen)

    adapter = NotionDocAdapter(NotionConfig(token="notion-secret"), AccessToken(value="notion-secret"))
    result = adapter.list_folders()

    assert result.ok is False
    assert result.error.code == AUTH_FAILED
    assert "notion-secret" not in result.error.message


# Mock adapter tests

def test_mock_list_folders():
    adapter = NotionMockDocAdapter()
    result = adapter.list_folders()
    assert result.ok is True
    assert result.data["total"] == 2
    names = [f["name"] for f in result.data["folders"]]
    assert "Project Notes" in names
    assert "Task Tracker" in names


def test_mock_list_documents():
    adapter = NotionMockDocAdapter()
    result = adapter.list_documents("page-001")
    assert result.ok is True
    assert result.data["total"] == 1
    assert result.data["documents"][0]["name"] == "Getting Started"


def test_mock_list_documents_wrong_folder():
    adapter = NotionMockDocAdapter()
    result = adapter.list_documents("nonexistent")
    assert result.ok is True
    assert result.data["total"] == 0


def test_mock_download_document():
    adapter = NotionMockDocAdapter()
    result = adapter.download_document("block-001")
    assert result.ok is True
    assert result.data.content == b"Notion mock document content.\n"


def test_mock_download_not_found():
    adapter = NotionMockDocAdapter()
    result = adapter.download_document("nonexistent")
    assert result.ok is False
    assert result.error["code"] == "NETWORK_ERROR"


def test_mock_search_documents_matches_folder_and_document_names():
    adapter = NotionMockDocAdapter()

    result = adapter.search_documents("project", limit=10)

    assert result.ok is True
    assert result.data["total"] == 1
    assert result.data["documents"][0]["id"] == "page-001"
    assert result.data["documents"][0]["name"] == "Project Notes"


# CLI integration tests

def test_notion_mock_list_folders_cli():
    exit_code, text = run_cli(["--backend", "notion", "list-folders", "--mock"])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "list_folders"
    assert payload["data"]["total"] == 2


def test_notion_mock_list_docs_cli():
    exit_code, text = run_cli(["--backend", "notion", "list-docs", "--mock", "--folder", "page-001"])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["documents"][0]["name"] == "Getting Started"


# Backend factory tests

def test_factory_name():
    factory = NotionBackendFactory()
    assert factory.name == "notion"


def test_factory_create_mock_adapter():
    factory = NotionBackendFactory()
    adapter = factory.create_mock_doc_adapter()
    result = adapter.list_folders()
    assert result.ok is True
