"""Google Drive document backend adapter."""

from mcp_docs_toolkit.adapters.google_drive.adapter import GoogleDriveBackendFactory
from mcp_docs_toolkit.adapters.registry import register_backend

register_backend(GoogleDriveBackendFactory())
