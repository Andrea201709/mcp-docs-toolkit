"""Confluence document backend adapter."""

from mcp_docs_toolkit.adapters.confluence.adapter import ConfluenceBackendFactory
from mcp_docs_toolkit.adapters.registry import register_backend

register_backend(ConfluenceBackendFactory())
