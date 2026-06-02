"""Backend registry — maps backend names to their factories."""

from __future__ import annotations

from typing import Dict

from mcp_docs_toolkit.adapters.base import BackendFactory

# Populated by register_backend(); each adapter module calls it at import time.
_BACKENDS: Dict[str, BackendFactory] = {}
_loaded = False


def register_backend(factory: BackendFactory) -> None:
    """Register a backend factory. Called by each adapter's __init__.py."""
    _BACKENDS[factory.name] = factory


def get_backend(name: str) -> BackendFactory:
    """Look up a registered backend by name. Raises KeyError if unknown."""
    if name not in available_backends():
        raise KeyError(
            f"Unknown backend {name!r}. Available: {', '.join(sorted(available_backends())) or '(none)'}"
        )
    return _BACKENDS[name]


def available_backends() -> list[str]:
    """Return sorted list of registered backend names."""
    _ensure_loaded()
    return sorted(_BACKENDS.keys())


def _ensure_loaded() -> None:
    """Import adapter packages on first access (triggers register_backend calls).

    Uses a dedicated flag instead of checking len(_BACKENDS) because individual
    adapter modules may be imported directly by tests before this function runs,
    which would populate _BACKENDS with a subset of backends.
    """
    global _loaded
    if _loaded:
        return
    _loaded = True
    import mcp_docs_toolkit.adapters.keycloak  # noqa: F401
    import mcp_docs_toolkit.adapters.notion  # noqa: F401
    import mcp_docs_toolkit.adapters.confluence  # noqa: F401
    import mcp_docs_toolkit.adapters.google_drive  # noqa: F401
