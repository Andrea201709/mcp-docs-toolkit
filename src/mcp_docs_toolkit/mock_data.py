"""Public example data for local mock demos."""

from __future__ import annotations


MOCK_PRINCIPAL = "user@example.com"
MOCK_CLIENT_ID = "docs-cli"
MOCK_CLIENT_SECRET = "example-secret"
MOCK_USERNAME = MOCK_PRINCIPAL
MOCK_PASSWORD = "example-password"
MOCK_ACCESS_TOKEN = "mock-access-token"
MOCK_REALM = "example-realm"
MOCK_BASE_URL = "http://127.0.0.1:8765"

MOCK_FOLDERS = [{"id": "F001", "name": "Example Folder", "parentId": None}]

MOCK_DOCUMENT_CONTENT = b"Example mock document bytes.\n"

MOCK_DOCUMENTS = [
    {
        "id": "D001",
        "name": "Example Document.pdf",
        "folderId": "F001",
        "mimeType": "application/pdf",
        "size": len(MOCK_DOCUMENT_CONTENT),
    }
]
