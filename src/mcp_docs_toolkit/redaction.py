"""String redaction helpers for secret-bearing diagnostics."""

from __future__ import annotations

from urllib.parse import quote, quote_plus


def redact_values(message: str, sensitive_values: tuple[str, ...]) -> str:
    safe_message = message
    for value in sensitive_values:
        if not value:
            continue
        variants = {value, quote(value, safe=""), quote_plus(value)}
        for variant in variants:
            safe_message = safe_message.replace(variant, "[REDACTED]")
    return safe_message
