"""Tests for the adapter registry."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from mcp_docs_toolkit.adapters import available_backends, get_backend
from mcp_docs_toolkit.models import AccessToken, ApiResult, AuthResult, ConfigResult, DownloadedDocument
from mcp_docs_toolkit.cli import main


def run_cli(argv, env=None):
    stream = StringIO()
    exit_code = main(argv=argv, env=env or {}, out=stream)
    return exit_code, stream.getvalue()


def test_available_backends_includes_all_four():
    backends = available_backends()
    assert "keycloak" in backends
    assert "notion" in backends
    assert "confluence" in backends
    assert "google-drive" in backends
    assert len(backends) == 4


def test_get_backend_returns_factory():
    backend = get_backend("keycloak")
    assert backend.name == "keycloak"
    assert len(backend.required_env_vars) > 0


def test_get_backend_unknown_raises_keyerror():
    try:
        get_backend("nonexistent")
        assert False, "Expected KeyError"
    except KeyError as exc:
        assert "nonexistent" in str(exc)


def test_backends_command_lists_all():
    exit_code, text = run_cli(["backends"])
    payload = json.loads(text)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "backends"
    assert len(payload["data"]["backends"]) == 4


def test_search_command_uses_default_mock_backend():
    exit_code, text = run_cli(["search", "--query", "example", "--mock"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "search"
    assert payload["data"]["total"] == 1
    assert payload["data"]["documents"][0]["id"] == "D001"


def test_search_command_supports_other_mock_backends():
    exit_code, text = run_cli(["--backend", "confluence", "search", "--query", "api", "--mock"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "search"
    assert payload["data"]["total"] == 1
    assert payload["data"]["documents"][0]["name"] == "API Design Guide"


def test_list_docs_mock_supports_cli_pagination():
    exit_code, text = run_cli(["--backend", "confluence", "list-docs", "--folder", "space-001", "--mock", "--page-size", "1"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["total"] == 1
    assert payload["data"]["documents"][0]["id"] == "page-001"
    assert payload["data"]["nextCursor"] == "1"

    exit_code, text = run_cli(["--backend", "confluence", "list-docs", "--folder", "space-001", "--mock", "--page-size", "1", "--cursor", "1"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["total"] == 1
    assert payload["data"]["documents"][0]["id"] == "page-002"
    assert "nextCursor" not in payload["data"]


def test_list_folders_mock_supports_cli_pagination():
    exit_code, text = run_cli(["--backend", "notion", "list-folders", "--mock", "--page-size", "1"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["total"] == 1
    assert payload["data"]["folders"][0]["id"] == "page-001"
    assert payload["data"]["nextCursor"] == "1"

    exit_code, text = run_cli(["--backend", "notion", "list-folders", "--mock", "--page-size", "1", "--cursor", "1"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["total"] == 1
    assert payload["data"]["folders"][0]["id"] == "db-001"
    assert "nextCursor" not in payload["data"]


def test_non_mock_command_reports_missing_backend_config():
    exit_code, text = run_cli(["--backend", "notion", "list-folders"], env={})
    payload = json.loads(text)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["stage"] == "config"
    assert payload["auth"]["tokenSource"] == "NOTION"
    assert "MCP_DOCS_NOTION_TOKEN" in payload["error"]["message"]


def test_non_mock_list_folders_routes_through_selected_adapter(monkeypatch):
    class FakeAuth:
        def authenticate(self):
            return AuthResult(ok=True, token=AccessToken(value="secret-token", principal="fake-user"))

    class FakeDocAdapter:
        def list_folders(self, root_id=None, page_cursor=None, page_size=100):
            return ApiResult(
                ok=True,
                data={
                    "folders": [{"id": "fake-folder", "name": "Fake Folder", "parentId": root_id}],
                    "total": 1,
                    "pageSize": page_size,
                    "cursor": page_cursor,
                },
            )

    class FakeBackend:
        name = "fake"
        required_env_vars = ("FAKE_TOKEN",)

        def load_config(self, env):
            return ConfigResult(ok=True, config={"token": env["FAKE_TOKEN"]})

        def create_auth(self, config):
            return FakeAuth()

        def create_doc_adapter(self, config, token):
            assert token.value == "secret-token"
            return FakeDocAdapter()

    monkeypatch.setattr("mcp_docs_toolkit.cli.get_backend", lambda name: FakeBackend())

    exit_code, text = run_cli(
        ["--backend", "fake", "list-folders", "--root", "ROOT", "--page-size", "7", "--cursor", "3"],
        env={"FAKE_TOKEN": "configured-secret"},
    )
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "list_folders"
    assert payload["auth"]["principal"] == "fake-user"
    assert payload["auth"]["tokenSource"] == "FAKE"
    assert payload["data"]["folders"][0]["parentId"] == "ROOT"
    assert payload["data"]["pageSize"] == 7
    assert payload["data"]["cursor"] == "3"
    assert "configured-secret" not in text
    assert "secret-token" not in text


def test_non_mock_download_routes_through_selected_adapter(monkeypatch, tmp_path):
    class FakeAuth:
        def authenticate(self):
            return AuthResult(ok=True, token=AccessToken(value="secret-token", principal="fake-user"))

    class FakeDocAdapter:
        def download_document(self, doc_id):
            return ApiResult(
                ok=True,
                data=DownloadedDocument(
                    filename=f"{doc_id}.txt",
                    content=b"fake content\n",
                    mime_type="text/plain",
                ),
            )

    class FakeBackend:
        name = "fake"
        required_env_vars = ("FAKE_TOKEN",)

        def load_config(self, env):
            return ConfigResult(ok=True, config={"token": env["FAKE_TOKEN"]})

        def create_auth(self, config):
            return FakeAuth()

        def create_doc_adapter(self, config, token):
            return FakeDocAdapter()

    monkeypatch.setattr("mcp_docs_toolkit.cli.get_backend", lambda name: FakeBackend())

    exit_code, text = run_cli(
        ["--backend", "fake", "download", "--doc-id", "doc-1", "--output", str(tmp_path)],
        env={"FAKE_TOKEN": "configured-secret"},
    )
    payload = json.loads(text)
    output_path = Path(payload["data"]["path"])

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "download"
    assert payload["auth"]["principal"] == "fake-user"
    assert payload["data"]["filename"] == "doc-1.txt"
    assert output_path.read_bytes() == b"fake content\n"
    assert output_path.parent == tmp_path
    assert "configured-secret" not in text
    assert "secret-token" not in text


def test_info_command_reports_each_backend_required_vars_without_values():
    env = {
        "MCP_DOCS_NOTION_TOKEN": "notion-secret",
        "MCP_DOCS_CONFLUENCE_URL": "https://example.atlassian.net/wiki",
        "MCP_DOCS_CONFLUENCE_EMAIL": "person@example.com",
        "MCP_DOCS_GOOGLE_ACCESS_TOKEN": "google-secret",
    }

    for backend_name in ("notion", "confluence", "google-drive"):
        exit_code, text = run_cli(["--backend", backend_name, "info"], env=env)
        payload = json.loads(text)
        assert exit_code == 0
        assert payload["ok"] is True
        assert payload["stage"] == "info"
        assert payload["data"]["backend"] == backend_name
        assert isinstance(payload["data"]["requiredVars"], dict)
        assert "notion-secret" not in text
        assert "google-secret" not in text
        assert "person@example.com" not in text


def test_login_check_notion_backend_missing_config():
    exit_code, text = run_cli(["--backend", "notion", "login", "--check"], env={})
    payload = json.loads(text)
    assert exit_code == 2
    assert payload["ok"] is False
    assert "MCP_DOCS_NOTION_TOKEN" in payload["error"]["message"]


def test_login_check_confluence_backend_missing_config():
    exit_code, text = run_cli(["--backend", "confluence", "login", "--check"], env={})
    payload = json.loads(text)
    assert exit_code == 2
    assert payload["ok"] is False
    assert "MCP_DOCS_CONFLUENCE_URL" in payload["error"]["message"]


def test_login_check_google_drive_backend_missing_config():
    exit_code, text = run_cli(["--backend", "google-drive", "login", "--check"], env={})
    payload = json.loads(text)
    assert exit_code == 2
    assert payload["ok"] is False
    assert "MCP_DOCS_GOOGLE_ACCESS_TOKEN" in payload["error"]["message"]
