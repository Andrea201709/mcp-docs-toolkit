"""Pluggable document backend adapters.

Usage::

    from mcp_docs_toolkit.adapters import get_backend, available_backends

    backend = get_backend("notion")
    config_result = backend.load_config(os.environ)
    if config_result.ok:
        auth = backend.create_auth(config_result.config)
        auth_result = auth.authenticate()
        doc = backend.create_doc_adapter(config_result.config, auth_result.token)
        result = doc.list_folders()
"""

from mcp_docs_toolkit.adapters.base import AuthAdapter, BackendFactory, DocAdapter
from mcp_docs_toolkit.adapters.registry import available_backends, get_backend, register_backend

__all__ = [
    "AuthAdapter",
    "BackendFactory",
    "DocAdapter",
    "available_backends",
    "get_backend",
    "register_backend",
]
