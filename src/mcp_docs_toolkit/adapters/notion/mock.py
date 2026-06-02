"""Notion mock document adapter."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.pagination import add_next_cursor, page_items
from mcp_docs_toolkit.models import ApiResult, Document, DownloadedDocument, Folder


_MOCK_FOLDERS = [
    {"id": "page-001", "name": "Project Notes", "parentId": None},
    {"id": "db-001", "name": "Task Tracker", "parentId": None},
]

_MOCK_DOCUMENTS = [
    {"id": "block-001", "name": "Getting Started", "folderId": "page-001", "mimeType": "text/plain", "size": 128},
]

_MOCK_CONTENT = b"Notion mock document content.\n"


class NotionMockDocAdapter:
    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        all_folders = [Folder(id=f["id"], name=f["name"], parent_id=f.get("parentId")).to_dict() for f in _MOCK_FOLDERS]
        folders, next_cursor = page_items(all_folders, page_cursor, page_size)
        return ApiResult(ok=True, data=add_next_cursor({"folders": folders, "total": len(folders)}, next_cursor))

    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        all_documents = [
            Document(id=d["id"], name=d["name"], folder_id=d["folderId"], mime_type=d.get("mimeType"), size=d.get("size")).to_dict()
            for d in _MOCK_DOCUMENTS
            if d["folderId"] == folder_id
        ]
        documents, next_cursor = page_items(all_documents, page_cursor, page_size)
        return ApiResult(ok=True, data=add_next_cursor({"documents": documents, "total": len(documents)}, next_cursor))

    def download_document(self, doc_id: str) -> ApiResult:
        doc = next((d for d in _MOCK_DOCUMENTS if d["id"] == doc_id), None)
        if doc is None:
            return ApiResult(ok=False, error={"code": "NETWORK_ERROR", "message": f"Document {doc_id} not found.", "retryable": False})
        return ApiResult(ok=True, data=DownloadedDocument(filename=doc["name"], content=_MOCK_CONTENT, mime_type=doc.get("mimeType")))

    def search_documents(self, query: str, limit: int = 10) -> ApiResult:
        needle = query.strip().lower()
        searchable_items = [
            Document(
                id=f["id"],
                name=f["name"],
                folder_id=f["id"],
                mime_type="notion/container",
            ).to_dict()
            for f in _MOCK_FOLDERS
        ] + [
            Document(
                id=d["id"],
                name=d["name"],
                folder_id=d["folderId"],
                mime_type=d.get("mimeType"),
                size=d.get("size"),
            ).to_dict()
            for d in _MOCK_DOCUMENTS
        ]
        matches = [
            item
            for item in searchable_items
            if not needle or needle in f"{item['id']} {item['name']} {item['folderId']}".lower()
        ]
        limited = matches[: max(limit, 0)]
        return ApiResult(ok=True, data={"documents": limited, "total": len(limited)})
