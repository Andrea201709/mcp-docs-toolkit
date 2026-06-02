"""Keycloak mock document adapter — returns hardcoded public data."""

from __future__ import annotations

from mcp_docs_toolkit.adapters.pagination import add_next_cursor, page_items
from mcp_docs_toolkit.mock_data import MOCK_DOCUMENT_CONTENT, MOCK_DOCUMENTS, MOCK_FOLDERS
from mcp_docs_toolkit.models import ApiResult, DownloadedDocument, Folder, Document


class KeycloakMockDocAdapter:
    """DocAdapter backed by in-memory mock data (no network, no credentials)."""

    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        all_folders = [
            Folder(id=f["id"], name=f["name"], parent_id=f.get("parentId")).to_dict()
            for f in MOCK_FOLDERS
        ]
        folders, next_cursor = page_items(all_folders, page_cursor, page_size)
        return ApiResult(ok=True, data=add_next_cursor({"folders": folders, "total": len(folders)}, next_cursor))

    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult:
        all_documents = [
            Document(
                id=d["id"],
                name=d["name"],
                folder_id=d["folderId"],
                mime_type=d.get("mimeType"),
                size=d.get("size"),
            ).to_dict()
            for d in MOCK_DOCUMENTS
            if d["folderId"] == folder_id
        ]
        documents, next_cursor = page_items(all_documents, page_cursor, page_size)
        return ApiResult(ok=True, data=add_next_cursor({"documents": documents, "total": len(documents)}, next_cursor))

    def download_document(self, doc_id: str) -> ApiResult:
        document = next((d for d in MOCK_DOCUMENTS if d["id"] == doc_id), None)
        if document is None:
            return ApiResult(
                ok=False,
                error={"code": "NETWORK_ERROR", "message": f"Document {doc_id} not found.", "retryable": False},
            )
        return ApiResult(
            ok=True,
            data=DownloadedDocument(
                filename=document["name"],
                content=MOCK_DOCUMENT_CONTENT,
                mime_type=document.get("mimeType"),
            ),
        )

    def search_documents(self, query: str, limit: int = 10) -> ApiResult:
        needle = query.strip().lower()
        documents = []
        for document in MOCK_DOCUMENTS:
            folder = next((f for f in MOCK_FOLDERS if f["id"] == document["folderId"]), None)
            searchable = " ".join(
                str(value)
                for value in (
                    document["id"],
                    document["name"],
                    document["folderId"],
                    folder["name"] if folder else "",
                )
            ).lower()
            if not needle or needle in searchable:
                documents.append(
                    Document(
                        id=document["id"],
                        name=document["name"],
                        folder_id=document["folderId"],
                        mime_type=document.get("mimeType"),
                        size=document.get("size"),
                    ).to_dict()
                )
        limited = documents[: max(limit, 0)]
        return ApiResult(ok=True, data={"documents": limited, "total": len(limited)})
