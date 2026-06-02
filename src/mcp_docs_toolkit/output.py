"""Structured JSON output helpers."""

from __future__ import annotations

import json
from typing import Any


SENSITIVE_KEYS = {
    "access_token",
    "authorization",
    "client_secret",
    "cookie",
    "mcpToken",
    "password",
    "refresh_token",
    "token",
}


def _is_sensitive_key(key: str) -> bool:
    return key.lower() in {item.lower() for item in SENSITIVE_KEYS}


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _is_sensitive_key(str(key)) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def success_response(stage: str, data: dict[str, Any], principal: str | None = None, token_source: str = "KEYCLOAK") -> dict[str, Any]:
    return {
        "ok": True,
        "stage": stage,
        "auth": {"tokenSource": token_source, "principal": principal},
        "data": data,
        "error": None,
    }


def error_response(
    stage: str,
    code: str,
    message: str,
    retryable: bool,
    principal: str | None = None,
    token_source: str = "KEYCLOAK",
) -> dict[str, Any]:
    return {
        "ok": False,
        "stage": stage,
        "auth": {"tokenSource": token_source, "principal": principal},
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        },
    }


def to_json(payload: dict[str, Any]) -> str:
    safe_payload = redact_secrets(payload)
    return json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
