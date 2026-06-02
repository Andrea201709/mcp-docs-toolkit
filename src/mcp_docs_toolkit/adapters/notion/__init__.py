"""Notion document backend adapter."""

from mcp_docs_toolkit.adapters.notion.adapter import NotionBackendFactory
from mcp_docs_toolkit.adapters.registry import register_backend

register_backend(NotionBackendFactory())
