"""Keycloak-compatible authentication helpers."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from mcp_docs_toolkit.adapters.keycloak._config_compat import Settings
from mcp_docs_toolkit.errors import AUTH_FAILED, NETWORK_ERROR
from mcp_docs_toolkit.models import AccessToken, AuthResult, ToolError
from mcp_docs_toolkit.redaction import redact_values


class ResponseLike(Protocol):
    def __enter__(self) -> "ResponseLike": ...

    def __exit__(self, exc_type, exc, tb) -> bool: ...

    def read(self) -> bytes: ...


Opener = Callable[..., ResponseLike]


def _token_url(settings: Settings) -> str:
    realm = quote(settings.keycloak_realm.strip("/"), safe="")
    return f"{settings.keycloak_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"


def _auth_error(message: str) -> AuthResult:
    return AuthResult(ok=False, error=ToolError(code=AUTH_FAILED, message=message, retryable=False))


def _network_error(message: str, sensitive_values: tuple[str, ...] = ()) -> AuthResult:
    return AuthResult(
        ok=False,
        error=ToolError(code=NETWORK_ERROR, message=redact_values(message, sensitive_values), retryable=True),
    )


def request_access_token(settings: Settings, opener: Opener = urlopen) -> AuthResult:
    form = {
        "grant_type": "password",
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "username": settings.username,
        "password": settings.password,
        "scope": "openid profile email",
    }
    request = Request(
        _token_url(settings),
        data=urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with opener(request, timeout=settings.timeout_seconds) as response:
            raw_body = response.read()
    except HTTPError as exc:
        if exc.code in {400, 401, 403}:
            return _auth_error("Keycloak rejected the username, password, or client credentials.")
        return _network_error(f"Keycloak token endpoint returned HTTP {exc.code}.")
    except (TimeoutError, URLError, OSError) as exc:
        return _network_error(str(exc), (settings.client_secret, settings.password))

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError):
        return _auth_error("Keycloak response was not valid JSON.")

    access_token = body.get("access_token")
    if not access_token:
        return _auth_error("Keycloak response did not contain access_token.")

    expires_in = body.get("expires_in")
    token_type = body.get("token_type") or "Bearer"
    return AuthResult(
        ok=True,
        token=AccessToken(
            value=str(access_token),
            expires_in=int(expires_in) if isinstance(expires_in, int) else None,
            token_type=str(token_type),
            principal=settings.username,
        ),
    )
