"""Google Drive mock document adapter."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.pagination import add_next_cursor, page_items
from mcp_docs_toolkit.models import ApiResult, Document, DownloadedDocument, Folder


_MOCK_FOLDERS = [
    {"id": "folder-001", "name": "My Drive", "parentId": None},
    {"id": "folder-002", "name": "Shared with me", "parentId": None},
]

_MOCK_DOCUMENTS = [
    {"id": "file-001", "name": "Quarterly Report.pdf", "folderId": "folder-001", "mimeType": "application/pdf", "size": 15360},
    {"id": "file-002", "name": "Meeting Notes.docx", "folderId": "folder-001", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "size": 8192},
]

_MOCK_CONTENT = b"Mock Google Drive file content.\n"


class GoogleDriveMockDocAdapter:
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
        documents = []
        for doc in _MOCK_DOCUMENTS:
            folder = next((f for f in _MOCK_FOLDERS if f["id"] == doc["folderId"]), None)
            searchable = f"{doc['id']} {doc['name']} {doc['folderId']} {folder['name'] if folder else ''}".lower()
            if not needle or needle in searchable:
                documents.append(
                    Document(
                        id=doc["id"],
                        name=doc["name"],
                        folder_id=doc["folderId"],
                        mime_type=doc.get("mimeType"),
                        size=doc.get("size"),
                    ).to_dict()
                )
        limited = documents[: max(limit, 0)]
        return ApiResult(ok=True, data={"documents": limited, "total": len(limited)})
