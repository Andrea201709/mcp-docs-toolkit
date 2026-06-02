"""Tests for the Confluence adapter."""

from __future__ import annotations

import base64
import json
from io import StringIO
from urllib.error import HTTPError

from mcp_docs_toolkit.errors import AUTH_FAILED
from mcp_docs_toolkit.adapters.confluence.config import ConfluenceConfig, load_confluence_config
from mcp_docs_toolkit.adapters.confluence.mock import ConfluenceMockDocAdapter
from mcp_docs_toolkit.adapters.confluence.adapter import ConfluenceAuthAdapter, ConfluenceBackendFactory, ConfluenceDocAdapter
from mcp_docs_toolkit.cli import main
from mcp_docs_toolkit.models import AccessToken


def run_cli(argv, env=None):
    stream = StringIO()
    exit_code = main(argv=argv, env=env or {}, out=stream)
    return exit_code, stream.getvalue()


# Config tests

def test_load_confluence_config_success():
    env = {
        "MCP_DOCS_CONFLUENCE_URL": "https://company.atlassian.net/wiki/",
        "MCP_DOCS_CONFLUENCE_EMAIL": "user@company.com",
        "MCP_DOCS_CONFLUENCE_API_TOKEN": "api-token-123",
    }
    result = load_confluence_config(env)
    assert result.ok is True
    assert isinstance(result.config, ConfluenceConfig)
    assert result.config.base_url == "https://company.atlassian.net/wiki"
    assert result.config.email == "user@company.com"
    assert result.config.timeout_seconds == 30


def test_load_confluence_config_missing_vars():
    result = load_confluence_config({})
    assert result.ok is False
    assert "MCP_DOCS_CONFLUENCE_URL" in result.error["message"]


def test_load_confluence_config_partial_missing():
    env = {"MCP_DOCS_CONFLUENCE_URL": "https://example.com"}
    result = load_confluence_config(env)
    assert result.ok is False
    assert "MCP_DOCS_CONFLUENCE_EMAIL" in result.error["message"]
    assert "MCP_DOCS_CONFLUENCE_API_TOKEN" in result.error["message"]


# Auth tests

def test_confluence_auth_returns_basic_token():
    config = ConfluenceConfig(base_url="https://example.com", email="user@test.com", api_token="my-token")
    auth = ConfluenceAuthAdapter(config)
    result = auth.authenticate()
    assert result.ok is True
    assert result.token.token_type == "Basic"
    assert result.token.principal == "user@test.com"
    decoded = base64.b64decode(result.token.value).decode("utf-8")
    assert decoded == "user@test.com:my-token"


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


def test_confluence_list_documents_gets_pages_and_normalizes_response(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["authorization"] = request.get_header("Authorization")
        seen["accept"] = request.get_header("Accept")
        return FakeResponse(
            json.dumps(
                {
                    "results": [
                        {
                            "id": "123",
                            "title": "Runbook",
                            "body": {"storage": {"value": "<p>Hello</p>"}},
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("mcp_docs_toolkit.adapters.confluence.adapter.urlopen", fake_urlopen)

    config = ConfluenceConfig(base_url="https://example.atlassian.net/wiki", email="user@example.com", api_token="api-secret")
    adapter = ConfluenceDocAdapter(config, AccessToken(value="basic-secret", token_type="Basic"))
    result = adapter.list_documents("SPACE")

    assert result.ok is True
    assert seen["url"] == "https://example.atlassian.net/wiki/rest/api/v2/pages?space-id=SPACE&limit=100"
    assert seen["method"] == "GET"
    assert seen["authorization"] == "Basic basic-secret"
    assert seen["accept"] == "application/json"
    assert result.data["documents"][0]["id"] == "123"
    assert result.data["documents"][0]["name"] == "Runbook"
    assert result.data["documents"][0]["folderId"] == "SPACE"


def test_confluence_http_401_returns_auth_failed_without_token(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr("mcp_docs_toolkit.adapters.confluence.adapter.urlopen", fake_urlopen)

    config = ConfluenceConfig(base_url="https://example.atlassian.net/wiki", email="user@example.com", api_token="api-secret")
    adapter = ConfluenceDocAdapter(config, AccessToken(value="basic-secret", token_type="Basic"))
    result = adapter.list_folders()

    assert result.ok is False
    assert result.error.code == AUTH_FAILED
    assert "basic-secret" not in result.error.message


# Mock adapter tests

def test_mock_list_folders():
    adapter = ConfluenceMockDocAdapter()
    result = adapter.list_folders()
    assert result.ok is True
    assert result.data["total"] == 2
    names = [f["name"] for f in result.data["folders"]]
    assert "Engineering" in names
    assert "Product" in names


def test_mock_list_documents():
    adapter = ConfluenceMockDocAdapter()
    result = adapter.list_documents("space-001")
    assert result.ok is True
    assert result.data["total"] == 2
    names = [d["name"] for d in result.data["documents"]]
    assert "Architecture Overview" in names
    assert "API Design Guide" in names


def test_mock_download_document():
    adapter = ConfluenceMockDocAdapter()
    result = adapter.download_document("page-001")
    assert result.ok is True
    assert b"Mock Confluence page content" in result.data.content


def test_mock_download_not_found():
    adapter = ConfluenceMockDocAdapter()
    result = adapter.download_document("nonexistent")
    assert result.ok is False
    assert result.error["code"] == "NETWORK_ERROR"


# CLI integration tests

def test_confluence_mock_list_folders_cli():
    exit_code, text = run_cli(["--backend", "confluence", "list-folders", "--mock"])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["total"] == 2


def test_confluence_mock_list_docs_cli():
    exit_code, text = run_cli(["--backend", "confluence", "list-docs", "--mock", "--folder", "space-001"])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["total"] == 2


# Factory tests

def test_factory_name():
    factory = ConfluenceBackendFactory()
    assert factory.name == "confluence"


def test_factory_create_mock_adapter():
    factory = ConfluenceBackendFactory()
    adapter = factory.create_mock_doc_adapter()
    result = adapter.list_folders()
    assert result.ok is True
