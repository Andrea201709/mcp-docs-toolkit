import json
from io import StringIO
from pathlib import Path

from mcp_docs_toolkit.cli import main
from mcp_docs_toolkit.errors import CONFIG_MISSING


def run_cli(argv, env=None):
    stream = StringIO()
    exit_code = main(argv=argv, env=env or {}, out=stream)
    return exit_code, stream.getvalue()


def assert_mock_secrets_absent(text):
    assert "mock-access-token" not in text
    assert "example-password" not in text
    assert "example-secret" not in text


def test_help_prints_usage_to_output():
    exit_code, text = run_cli(["--help"])

    assert exit_code == 0
    assert "usage: mcp-docs" in text
    assert "list-folders" in text


def test_login_check_reports_missing_config_as_json():
    exit_code, text = run_cli(["login", "--check"], env={})
    payload = json.loads(text)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["stage"] == "config"
    assert payload["error"]["code"] == CONFIG_MISSING
    assert "MCP_DOCS_KEYCLOAK_URL" in payload["error"]["message"]


def test_login_check_respects_explicit_empty_env(monkeypatch):
    monkeypatch.setenv("MCP_DOCS_KEYCLOAK_URL", "https://idp.example.com")
    monkeypatch.setenv("MCP_DOCS_KEYCLOAK_REALM", "example-realm")
    monkeypatch.setenv("MCP_DOCS_CLIENT_ID", "docs-cli")
    monkeypatch.setenv("MCP_DOCS_CLIENT_SECRET", "secret-value")
    monkeypatch.setenv("MCP_DOCS_USERNAME", "user@example.com")
    monkeypatch.setenv("MCP_DOCS_PASSWORD", "password-value")
    monkeypatch.setenv("MCP_DOCS_API_URL", "https://docs-api.example.com")

    exit_code, text = run_cli(["login", "--check"], env={})
    payload = json.loads(text)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == CONFIG_MISSING


def test_login_check_accepts_complete_config_without_printing_secrets():
    env = {
        "MCP_DOCS_KEYCLOAK_URL": "https://idp.example.com",
        "MCP_DOCS_KEYCLOAK_REALM": "example-realm",
        "MCP_DOCS_CLIENT_ID": "docs-cli",
        "MCP_DOCS_CLIENT_SECRET": "secret-value",
        "MCP_DOCS_USERNAME": "user@example.com",
        "MCP_DOCS_PASSWORD": "password-value",
        "MCP_DOCS_API_URL": "https://docs-api.example.com",
    }

    exit_code, text = run_cli(["login", "--check"], env=env)
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "login_check"
    assert payload["data"] == {"configured": True}
    assert "secret-value" not in text
    assert "password-value" not in text


def test_list_folders_without_mock_reports_missing_config():
    exit_code, text = run_cli(["list-folders", "--root", "F001"], env={})
    payload = json.loads(text)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["stage"] == "config"
    assert payload["error"]["code"] == CONFIG_MISSING
    assert "MCP_DOCS_KEYCLOAK_URL" in payload["error"]["message"]


def test_list_folders_mock_returns_public_data_without_secrets():
    exit_code, text = run_cli(["list-folders", "--mock"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "list_folders"
    assert payload["data"] == {
        "folders": [{"id": "F001", "name": "Example Folder", "parentId": None}],
        "total": 1,
    }
    assert_mock_secrets_absent(text)


def test_list_docs_without_mock_reports_missing_config():
    exit_code, text = run_cli(["list-docs", "--folder", "F001"], env={})
    payload = json.loads(text)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["stage"] == "config"
    assert payload["error"]["code"] == CONFIG_MISSING
    assert "MCP_DOCS_KEYCLOAK_URL" in payload["error"]["message"]


def test_list_docs_mock_returns_public_data():
    exit_code, text = run_cli(["list-docs", "--mock", "--folder", "F001"], env={})
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "list_docs"
    assert payload["data"] == {
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
    assert_mock_secrets_absent(text)


def test_download_without_mock_reports_missing_config():
    exit_code, text = run_cli(["download", "--doc-id", "D001", "--output", "downloads"], env={})
    payload = json.loads(text)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["stage"] == "config"
    assert payload["error"]["code"] == CONFIG_MISSING
    assert "MCP_DOCS_KEYCLOAK_URL" in payload["error"]["message"]


def test_download_mock_writes_file_and_returns_metadata(tmp_path):
    exit_code, text = run_cli(["download", "--mock", "--doc-id", "D001", "--output", str(tmp_path)], env={})
    payload = json.loads(text)

    output_path = Path(payload["data"]["path"])

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "download"
    assert payload["data"]["filename"] == "Example Document.pdf"
    assert payload["data"]["mimeType"] == "application/pdf"
    assert payload["data"]["size"] == 29
    assert output_path.read_bytes() == b"Example mock document bytes.\n"
    assert output_path.parent == tmp_path
    assert_mock_secrets_absent(text)


def test_download_mock_rejects_unsafe_filename(monkeypatch, tmp_path):
    from mcp_docs_toolkit.adapters.keycloak.mock import KeycloakMockDocAdapter
    from mcp_docs_toolkit.models import ApiResult, DownloadedDocument

    unsafe_document = DownloadedDocument(
        filename="../escape.pdf",
        content=b"unsafe",
        mime_type="application/pdf",
    )
    monkeypatch.setattr(
        KeycloakMockDocAdapter,
        "download_document",
        lambda self, doc_id: ApiResult(ok=True, data=unsafe_document),
    )

    exit_code, text = run_cli(["download", "--mock", "--doc-id", "D001", "--output", str(tmp_path)], env={})
    payload = json.loads(text)

    assert exit_code == 3
    assert payload["ok"] is False
    assert payload["stage"] == "download"
    assert "Unsafe download filename" in payload["error"]["message"]
    assert not (tmp_path.parent / "escape.pdf").exists()


def test_info_reports_required_vars_without_values():
    env = {
        "MCP_DOCS_KEYCLOAK_URL": "https://idp.example.com",
        "MCP_DOCS_KEYCLOAK_REALM": "example-realm",
        "MCP_DOCS_CLIENT_SECRET": "secret-value",
    }

    exit_code, text = run_cli(["info"], env=env)
    payload = json.loads(text)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["stage"] == "info"
    assert payload["data"]["backend"] == "keycloak"
    assert payload["data"]["configured"] is False
    assert payload["data"]["requiredVars"]["MCP_DOCS_KEYCLOAK_URL"] is True
    assert payload["data"]["requiredVars"]["MCP_DOCS_PASSWORD"] is False
    assert "secret-value" not in text
    assert "https://idp.example.com" not in text
