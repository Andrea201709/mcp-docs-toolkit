import json
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

from mcp_docs_toolkit.auth import request_access_token
from mcp_docs_toolkit.config import Settings
from mcp_docs_toolkit.errors import AUTH_FAILED, NETWORK_ERROR


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
        keycloak_url="https://idp.example.com/",
        keycloak_realm="example-realm",
        client_id="docs-cli",
        client_secret="example-secret",
        username="user@example.com",
        password="example-password",
        api_url="https://docs-api.example.com",
        timeout_seconds=7,
    )


def settings_with_encoded_credentials():
    return Settings(
        keycloak_url="https://idp.example.com/",
        keycloak_realm="example-realm",
        client_id="docs-cli",
        client_secret="s/cret",
        username="user@example.com",
        password="p@ss word",
        api_url="https://docs-api.example.com",
        timeout_seconds=7,
    )


def test_request_access_token_success_posts_password_grant():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return FakeResponse({"access_token": "token-value", "expires_in": 300, "token_type": "Bearer"})

    result = request_access_token(settings(), opener=opener)

    assert result.ok is True
    assert result.error is None
    assert result.token.value == "token-value"
    assert result.token.expires_in == 300
    assert result.token.token_type == "Bearer"
    assert result.token.principal == "user@example.com"
    assert "token-value" not in repr(result.token)

    request, timeout = calls[0]
    assert timeout == 7
    assert request.full_url == "https://idp.example.com/realms/example-realm/protocol/openid-connect/token"
    assert request.get_method() == "POST"
    assert request.headers["Content-type"] == "application/x-www-form-urlencoded"
    body = parse_qs(request.data.decode("utf-8"))
    assert body["grant_type"] == ["password"]
    assert body["client_id"] == ["docs-cli"]
    assert body["client_secret"] == ["example-secret"]
    assert body["username"] == ["user@example.com"]
    assert body["password"] == ["example-password"]
    assert body["scope"] == ["openid profile email"]


def test_request_access_token_http_401_returns_auth_failed():
    def opener(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", hdrs=None, fp=None)

    result = request_access_token(settings(), opener=opener)

    assert result.ok is False
    assert result.token is None
    assert result.error.code == AUTH_FAILED
    assert result.error.retryable is False


def test_request_access_token_missing_token_returns_auth_failed():
    def opener(request, timeout):
        return FakeResponse({"expires_in": 300})

    result = request_access_token(settings(), opener=opener)

    assert result.ok is False
    assert result.error.code == AUTH_FAILED
    assert result.error.message == "Keycloak response did not contain access_token."


def test_request_access_token_invalid_json_returns_auth_failed():
    def opener(request, timeout):
        return FakeResponse(b"not json")

    result = request_access_token(settings(), opener=opener)

    assert result.ok is False
    assert result.error.code == AUTH_FAILED
    assert "valid JSON" in result.error.message


def test_request_access_token_network_error_is_retryable():
    def opener(request, timeout):
        raise URLError("connection refused")

    result = request_access_token(settings(), opener=opener)

    assert result.ok is False
    assert result.token is None
    assert result.error.code == NETWORK_ERROR
    assert result.error.retryable is True
    assert "connection refused" in result.error.message


def test_request_access_token_network_error_redacts_credentials():
    def opener(request, timeout):
        raise URLError("client_secret=example-secret&password=example-password")

    result = request_access_token(settings(), opener=opener)

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert "example-secret" not in result.error.message
    assert "example-password" not in result.error.message
    assert "[REDACTED]" in result.error.message


def test_request_access_token_network_error_redacts_encoded_credentials():
    def opener(request, timeout):
        raise URLError("client_secret=s%2Fcret&password=p%40ss+word")

    result = request_access_token(settings_with_encoded_credentials(), opener=opener)

    assert result.ok is False
    assert result.error.code == NETWORK_ERROR
    assert "s/cret" not in result.error.message
    assert "s%2Fcret" not in result.error.message
    assert "p@ss word" not in result.error.message
    assert "p%40ss+word" not in result.error.message
    assert "[REDACTED]" in result.error.message
