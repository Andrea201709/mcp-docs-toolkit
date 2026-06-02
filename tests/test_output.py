import json

from mcp_docs_toolkit.output import error_response, redact_secrets, success_response, to_json


def test_success_response_shape():
    payload = success_response(
        stage="list_folders",
        principal="user@example.com",
        data={"folders": [], "total": 0},
    )

    assert payload == {
        "ok": True,
        "stage": "list_folders",
        "auth": {"tokenSource": "KEYCLOAK", "principal": "user@example.com"},
        "data": {"folders": [], "total": 0},
        "error": None,
    }


def test_error_response_shape():
    payload = error_response(
        stage="config",
        code="CONFIG_MISSING",
        message="Missing required environment variables: MCP_DOCS_API_URL",
        retryable=False,
    )

    assert payload["ok"] is False
    assert payload["stage"] == "config"
    assert payload["auth"] == {"tokenSource": "KEYCLOAK", "principal": None}
    assert payload["data"] is None
    assert payload["error"] == {
        "code": "CONFIG_MISSING",
        "message": "Missing required environment variables: MCP_DOCS_API_URL",
        "retryable": False,
    }


def test_redact_secrets_removes_sensitive_values():
    value = {
        "access_token": "abc.def.ghi",
        "password": "secret-password",
        "nested": {"client_secret": "client-secret", "safe": "visible"},
        "items": [{"Authorization": "Bearer token-value"}],
    }

    redacted = redact_secrets(value)

    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["client_secret"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "visible"
    assert redacted["items"][0]["Authorization"] == "[REDACTED]"


def test_to_json_outputs_sorted_pretty_json_without_secrets():
    payload = {"password": "secret-password", "ok": True}

    text = to_json(payload)
    decoded = json.loads(text)
    lines = text.splitlines()

    assert decoded == {"ok": True, "password": "[REDACTED]"}
    assert lines[1].startswith('  "ok"')
    assert lines[2].startswith('  "password"')
    assert "secret-password" not in text
    assert text.endswith("\n")
