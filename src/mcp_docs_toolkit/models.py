"""Small data models for mcp-docs-toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolError:
    code: str
    message: str
    retryable: bool

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


@dataclass(frozen=True)
class AccessToken:
    value: str = field(repr=False)
    expires_in: int | None = None
    token_type: str = "Bearer"
    principal: str | None = None


@dataclass(frozen=True)
class Folder:
    id: str
    name: str
    parent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "parentId": self.parent_id}


@dataclass(frozen=True)
class Document:
    id: str
    name: str
    folder_id: str
    mime_type: str | None = None
    size: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "folderId": self.folder_id,
            "mimeType": self.mime_type,
            "size": self.size,
        }


@dataclass(frozen=True)
class DownloadedDocument:
    filename: str
    content: bytes = field(repr=False)
    mime_type: str | None = None


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    token: AccessToken | None = None
    error: ToolError | None = None


@dataclass(frozen=True)
class ApiResult:
    ok: bool
    data: Any | None = None
    error: ToolError | None = None


@dataclass(frozen=True)
class ConfigResult:
    ok: bool
    config: Any | None = None
    error: dict[str, object] | None = None
