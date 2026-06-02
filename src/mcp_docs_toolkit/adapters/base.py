"""Protocol definitions for pluggable document backends."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from mcp_docs_toolkit.errors import NOT_IMPLEMENTED
from mcp_docs_toolkit.models import ApiResult, AuthResult, AccessToken, ConfigResult, ToolError


class AuthAdapter(Protocol):
    """Backend-specific authentication."""

    def authenticate(self) -> AuthResult: ...


class DocAdapter(Protocol):
    """Uniform document operations across all backends."""

    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult: ...

    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult: ...

    def download_document(self, doc_id: str) -> ApiResult: ...

    def search_documents(self, query: str, limit: int = 10) -> ApiResult:
        return ApiResult(
            ok=False,
            error=ToolError(
                code=NOT_IMPLEMENTED,
                message="Document search is not implemented for this backend.",
                retryable=False,
            ),
        )


class BackendFactory(Protocol):
    """Creates auth and doc adapters from environment variables."""

    name: str
    required_env_vars: Sequence[str]

    def load_config(self, env: Mapping[str, str]) -> ConfigResult: ...

    def create_auth(self, config: Any) -> AuthAdapter: ...

    def create_doc_adapter(self, config: Any, token: AccessToken) -> DocAdapter: ...

    def create_mock_doc_adapter(self) -> DocAdapter: ...
