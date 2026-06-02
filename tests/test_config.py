from mcp_docs_toolkit.config import REQUIRED_ENV_VARS, Settings, load_settings
from mcp_docs_toolkit.errors import CONFIG_INVALID, CONFIG_MISSING


def complete_env():
    return {
        "MCP_DOCS_KEYCLOAK_URL": "https://idp.example.com",
        "MCP_DOCS_KEYCLOAK_REALM": "example-realm",
        "MCP_DOCS_CLIENT_ID": "docs-cli",
        "MCP_DOCS_CLIENT_SECRET": "example-secret",
        "MCP_DOCS_USERNAME": "user@example.com",
        "MCP_DOCS_PASSWORD": "example-password",
        "MCP_DOCS_API_URL": "https://docs-api.example.com",
    }


def test_required_env_vars_are_explicit():
    assert REQUIRED_ENV_VARS == (
        "MCP_DOCS_KEYCLOAK_URL",
        "MCP_DOCS_KEYCLOAK_REALM",
        "MCP_DOCS_CLIENT_ID",
        "MCP_DOCS_CLIENT_SECRET",
        "MCP_DOCS_USERNAME",
        "MCP_DOCS_PASSWORD",
        "MCP_DOCS_API_URL",
    )


def test_load_settings_success_with_defaults():
    result = load_settings(complete_env())

    assert result.ok is True
    assert result.error is None
    assert result.settings == Settings(
        keycloak_url="https://idp.example.com",
        keycloak_realm="example-realm",
        client_id="docs-cli",
        client_secret="example-secret",
        username="user@example.com",
        password="example-password",
        api_url="https://docs-api.example.com",
        timeout_seconds=30,
        output_dir="downloads",
        verify_tls=True,
    )


def test_settings_repr_hides_sensitive_values():
    result = load_settings(complete_env())

    settings_repr = repr(result.settings)

    assert "example-secret" not in settings_repr
    assert "example-password" not in settings_repr
    assert "user@example.com" in settings_repr


def test_load_settings_reports_missing_values():
    env = complete_env()
    del env["MCP_DOCS_API_URL"]

    result = load_settings(env)

    assert result.ok is False
    assert result.settings is None
    assert result.error == {
        "code": CONFIG_MISSING,
        "message": "Missing required environment variables: MCP_DOCS_API_URL",
        "retryable": False,
    }


def test_load_settings_rejects_invalid_timeout():
    env = complete_env()
    env["MCP_DOCS_TIMEOUT_SECONDS"] = "zero"

    result = load_settings(env)

    assert result.ok is False
    assert result.settings is None
    assert result.error == {
        "code": CONFIG_INVALID,
        "message": "MCP_DOCS_TIMEOUT_SECONDS must be an integer greater than 0.",
        "retryable": False,
    }


def test_load_settings_parses_optional_values():
    env = complete_env()
    env["MCP_DOCS_TIMEOUT_SECONDS"] = "9"
    env["MCP_DOCS_OUTPUT_DIR"] = "custom-downloads"
    env["MCP_DOCS_VERIFY_TLS"] = "false"

    result = load_settings(env)

    assert result.ok is True
    assert result.settings.timeout_seconds == 9
    assert result.settings.output_dir == "custom-downloads"
    assert result.settings.verify_tls is False
