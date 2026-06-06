"""Command-line interface for mcp-docs-toolkit."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from contextlib import redirect_stdout
from typing import Mapping, Sequence, TextIO

from mcp_docs_toolkit import __version__
from mcp_docs_toolkit.adapters import available_backends, get_backend
from mcp_docs_toolkit.adapters.base import BackendFactory
from mcp_docs_toolkit.auth import request_access_token
from mcp_docs_toolkit.client import DocumentApiClient
from mcp_docs_toolkit.config import load_settings
from mcp_docs_toolkit.errors import DOWNLOAD_WRITE_FAILED, NETWORK_ERROR, NOT_IMPLEMENTED
from mcp_docs_toolkit.mock_transport import mock_opener, mock_settings
from mcp_docs_toolkit.models import AccessToken, ApiResult, AuthResult, DownloadedDocument
from mcp_docs_toolkit.output import error_response, success_response, to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp-docs")
    parser.add_argument("--backend", default=None, help="Document backend to use (default: keycloak). Use 'mcp-docs backends' to list options.")
    parser.add_argument("--version", action="store_true", help="Print the mcp-docs version and exit.")
    subparsers = parser.add_subparsers(dest="command")

    backends_parser = subparsers.add_parser("backends", help="List available document backends.")

    info_parser = subparsers.add_parser("info", help="Show backend configuration requirements without revealing values.")

    login_parser = subparsers.add_parser("login", help="Check backend configuration.")
    login_parser.add_argument("--check", action="store_true", help="Validate configuration without making a network call.")

    folders_parser = subparsers.add_parser("list-folders", help="List authorized document folders.")
    folders_parser.add_argument("--root", default=None, help="Optional root folder id.")
    folders_parser.add_argument("--cursor", default=None, help="Optional pagination cursor.")
    folders_parser.add_argument("--page-size", type=int, default=100, help="Maximum number of items to return.")
    folders_parser.add_argument("--mock", action="store_true", help="Use local mock data.")

    docs_parser = subparsers.add_parser("list-docs", help="List documents under a folder.")
    docs_parser.add_argument("--folder", required=True, help="Folder id to query.")
    docs_parser.add_argument("--cursor", default=None, help="Optional pagination cursor.")
    docs_parser.add_argument("--page-size", type=int, default=100, help="Maximum number of items to return.")
    docs_parser.add_argument("--mock", action="store_true", help="Use local mock data.")

    search_parser = subparsers.add_parser("search", help="Search documents by text query.")
    search_parser.add_argument("--query", required=True, help="Search text.")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results.")
    search_parser.add_argument("--mock", action="store_true", help="Use local mock data.")

    download_parser = subparsers.add_parser("download", help="Download a document by id.")
    download_parser.add_argument("--doc-id", required=True, help="Document id to download.")
    download_parser.add_argument("--output", default="downloads", help="Output directory.")
    download_parser.add_argument("--mock", action="store_true", help="Use local mock data.")

    return parser


def _write(out: TextIO, payload: dict[str, object]) -> None:
    out.write(to_json(payload))


def _resolve_backend(name: str | None, out: TextIO) -> BackendFactory | None:
    backend_name = name or "keycloak"
    try:
        return get_backend(backend_name)
    except KeyError as exc:
        _write(
            out,
            error_response(
                stage="config",
                code="CONFIG_MISSING",
                message=str(exc),
                retryable=False,
            ),
        )
        return None


def _handle_backends(out: TextIO) -> int:
    names = available_backends()
    _write(out, success_response(stage="backends", data={"backends": names, "total": len(names)}, token_source="REGISTRY"))
    return 0


def _handle_info(env: Mapping[str, str], out: TextIO, backend_name: str | None) -> int:
    backend = _resolve_backend(backend_name, out)
    if backend is None:
        return 2
    required_vars = {name: bool(env.get(name)) for name in backend.required_env_vars}
    _write(
        out,
        success_response(
            stage="info",
            data={
                "backend": backend.name,
                "requiredVars": required_vars,
                "configured": all(required_vars.values()),
            },
            token_source=backend.name.upper().replace("-", "_"),
        ),
    )
    return 0


def _handle_login_check(env: Mapping[str, str], out: TextIO, backend_name: str | None) -> int:
    # Legacy keycloak login check for backward compat
    if backend_name is None or backend_name == "keycloak":
        result = load_settings(env)
        if not result.ok:
            assert result.error is not None
            _write(
                out,
                error_response(
                    stage="config",
                    code=str(result.error["code"]),
                    message=str(result.error["message"]),
                    retryable=bool(result.error["retryable"]),
                ),
            )
            return 2
        _write(out, success_response(stage="login_check", principal=result.settings.username, data={"configured": True}))
        return 0

    backend = _resolve_backend(backend_name, out)
    if backend is None:
        return 2
    config_result = backend.load_config(env)
    if not config_result.ok:
        assert config_result.error is not None
        return _write_config_error(config_result.error, out, token_source=_token_source(backend.name))
    _write(out, success_response(stage="login_check", data={"configured": True, "backend": backend_name}))
    return 0


def _token_source(backend_name: str) -> str:
    return backend_name.upper().replace("-", "_")


def _write_config_error(result_error: dict[str, object], out: TextIO, token_source: str = "KEYCLOAK") -> int:
    _write(
        out,
        error_response(
            stage="config",
            code=str(result_error["code"]),
            message=str(result_error["message"]),
            retryable=bool(result_error["retryable"]),
            token_source=token_source,
        ),
    )
    return 2


def _not_implemented(stage: str, out: TextIO, backend_name: str | None) -> int:
    selected_backend = backend_name or "keycloak"
    login_command = "mcp-docs login --check" if selected_backend == "keycloak" else f"mcp-docs --backend {selected_backend} login --check"
    _write(
        out,
        error_response(
            stage=stage,
            code=NOT_IMPLEMENTED,
            message=(
                f"{stage} network behavior is planned for a later batch. "
                f"This backend requires environment variables. Use '{login_command}' "
                "to see what is missing, or add --mock for a local demo."
            ),
            retryable=False,
            token_source=selected_backend.upper().replace("-", "_"),
        ),
    )
    return 3


def _write_auth_error(stage: str, result: AuthResult, out: TextIO) -> int:
    assert result.error is not None
    _write(
        out,
        error_response(
            stage=stage,
            code=result.error.code,
            message=result.error.message,
            retryable=result.error.retryable,
        ),
    )
    return 2


def _error_code(error: object) -> str:
    if isinstance(error, dict):
        return str(error["code"])
    return str(error.code)  # type: ignore[attr-defined]


def _error_message(error: object) -> str:
    if isinstance(error, dict):
        return str(error["message"])
    return str(error.message)  # type: ignore[attr-defined]


def _error_retryable(error: object) -> bool:
    if isinstance(error, dict):
        return bool(error["retryable"])
    return bool(error.retryable)  # type: ignore[attr-defined]


def _write_api_result(stage: str, result: ApiResult, principal: str | None, out: TextIO, token_source: str = "KEYCLOAK") -> int:
    if result.ok:
        assert isinstance(result.data, dict)
        _write(out, success_response(stage=stage, principal=principal, data=result.data, token_source=token_source))
        return 0
    assert result.error is not None
    _write(
        out,
        error_response(
            stage=stage,
            code=_error_code(result.error),
            message=_error_message(result.error),
            retryable=_error_retryable(result.error),
            principal=principal,
            token_source=token_source,
        ),
    )
    return 3


def _write_download_error(out: TextIO, message: str, token_source: str, principal: str | None = None) -> int:
    _write(
        out,
        error_response(
            stage="download",
            code=DOWNLOAD_WRITE_FAILED,
            message=message,
            retryable=False,
            principal=principal,
            token_source=token_source,
        ),
    )
    return 3


def _legacy_mock_client(stage: str, out: TextIO) -> tuple[DocumentApiClient | None, str | None, int | None]:
    """Legacy keycloak mock path for backward compatibility."""
    settings = mock_settings()
    auth_result = request_access_token(settings, opener=mock_opener)
    if not auth_result.ok or auth_result.token is None:
        return None, None, _write_auth_error(stage, auth_result, out)
    return DocumentApiClient(settings, auth_result.token, opener=mock_opener), auth_result.token.principal, None


def _handle_mock_list_folders(root_id: str | None, page_cursor: str | None, page_size: int, out: TextIO, backend_name: str | None) -> int:
    backend = _resolve_backend(backend_name, out)
    if backend is None:
        return 2
    mock_adapter = backend.create_mock_doc_adapter()
    result = mock_adapter.list_folders(root_id=root_id, page_cursor=page_cursor, page_size=page_size)
    return _write_api_result("list_folders", result, None, out, token_source=backend.name.upper().replace("-", "_"))


def _handle_mock_list_docs(folder_id: str, page_cursor: str | None, page_size: int, out: TextIO, backend_name: str | None) -> int:
    backend = _resolve_backend(backend_name, out)
    if backend is None:
        return 2
    mock_adapter = backend.create_mock_doc_adapter()
    result = mock_adapter.list_documents(folder_id=folder_id, page_cursor=page_cursor, page_size=page_size)
    return _write_api_result("list_docs", result, None, out, token_source=backend.name.upper().replace("-", "_"))


def _load_backend_adapter(env: Mapping[str, str], out: TextIO, backend_name: str | None) -> tuple[BackendFactory | None, object | None, AccessToken | None, int | None]:
    backend = _resolve_backend(backend_name, out)
    if backend is None:
        return None, None, None, 2
    config_result = backend.load_config(env)
    if not config_result.ok:
        assert config_result.error is not None
        return None, None, None, _write_config_error(config_result.error, out, token_source=_token_source(backend.name))
    auth = backend.create_auth(config_result.config)
    auth_result = auth.authenticate()
    if not auth_result.ok or auth_result.token is None:
        return None, None, None, _write_auth_error("auth", auth_result, out)
    return backend, backend.create_doc_adapter(config_result.config, auth_result.token), auth_result.token, None


def _handle_list_folders(env: Mapping[str, str], root_id: str | None, page_cursor: str | None, page_size: int, out: TextIO, backend_name: str | None) -> int:
    backend, adapter, token, early_exit = _load_backend_adapter(env, out, backend_name)
    if early_exit is not None:
        return early_exit
    assert backend is not None and adapter is not None and token is not None
    result = adapter.list_folders(root_id=root_id, page_cursor=page_cursor, page_size=page_size)  # type: ignore[attr-defined]
    return _write_api_result("list_folders", result, token.principal, out, token_source=_token_source(backend.name))


def _handle_list_docs(env: Mapping[str, str], folder_id: str, page_cursor: str | None, page_size: int, out: TextIO, backend_name: str | None) -> int:
    backend, adapter, token, early_exit = _load_backend_adapter(env, out, backend_name)
    if early_exit is not None:
        return early_exit
    assert backend is not None and adapter is not None and token is not None
    result = adapter.list_documents(folder_id=folder_id, page_cursor=page_cursor, page_size=page_size)  # type: ignore[attr-defined]
    return _write_api_result("list_docs", result, token.principal, out, token_source=_token_source(backend.name))


def _handle_mock_search(query: str, limit: int, out: TextIO, backend_name: str | None) -> int:
    backend = _resolve_backend(backend_name, out)
    if backend is None:
        return 2
    mock_adapter = backend.create_mock_doc_adapter()
    result = mock_adapter.search_documents(query=query, limit=limit)
    return _write_api_result("search", result, None, out, token_source=backend.name.upper().replace("-", "_"))


def _handle_search(env: Mapping[str, str], query: str, limit: int, out: TextIO, backend_name: str | None) -> int:
    backend, adapter, token, early_exit = _load_backend_adapter(env, out, backend_name)
    if early_exit is not None:
        return early_exit
    assert backend is not None and adapter is not None and token is not None
    search_documents = getattr(adapter, "search_documents", None)
    if search_documents is None:
        return _not_implemented("search", out, backend.name)
    result = search_documents(query=query, limit=limit)
    return _write_api_result("search", result, token.principal, out, token_source=_token_source(backend.name))


def _safe_download_path(output_dir: str, filename: str) -> Path | None:
    candidate_name = Path(filename)
    if not filename or candidate_name.is_absolute() or candidate_name.name != filename or ".." in candidate_name.parts:
        return None
    return Path(output_dir) / candidate_name.name


def _handle_mock_download(doc_id: str, output_dir: str, out: TextIO, backend_name: str | None) -> int:
    backend = _resolve_backend(backend_name, out)
    if backend is None:
        return 2
    mock_adapter = backend.create_mock_doc_adapter()
    result = mock_adapter.download_document(doc_id=doc_id)
    token_src = backend.name.upper().replace("-", "_")
    if not result.ok:
        return _write_api_result("download", result, None, out, token_source=token_src)
    assert isinstance(result.data, DownloadedDocument)
    output_path = _safe_download_path(output_dir, result.data.filename)
    if output_path is None:
        _write(
            out,
            error_response(
                stage="download",
                code=NETWORK_ERROR,
                message="Unsafe download filename returned by document API.",
                retryable=False,
                token_source=token_src,
            ),
        )
        return 3
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result.data.content)
    except OSError:
        return _write_download_error(out, "Unable to write downloaded document to output directory.", token_src)
    _write(
        out,
        success_response(
            stage="download",
            data={
                "filename": result.data.filename,
                "path": str(output_path),
                "mimeType": result.data.mime_type,
                "size": len(result.data.content),
            },
            token_source=token_src,
        ),
    )
    return 0


def _write_downloaded_document(result: ApiResult, output_dir: str, out: TextIO, token_source: str, principal: str | None = None) -> int:
    if not result.ok:
        return _write_api_result("download", result, principal, out, token_source=token_source)
    assert isinstance(result.data, DownloadedDocument)
    output_path = _safe_download_path(output_dir, result.data.filename)
    if output_path is None:
        _write(
            out,
            error_response(
                stage="download",
                code=NETWORK_ERROR,
                message="Unsafe download filename returned by document API.",
                retryable=False,
                principal=principal,
                token_source=token_source,
            ),
        )
        return 3
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result.data.content)
    except OSError:
        return _write_download_error(out, "Unable to write downloaded document to output directory.", token_source, principal=principal)
    _write(
        out,
        success_response(
            stage="download",
            principal=principal,
            data={
                "filename": result.data.filename,
                "path": str(output_path),
                "mimeType": result.data.mime_type,
                "size": len(result.data.content),
            },
            token_source=token_source,
        ),
    )
    return 0


def _handle_download(env: Mapping[str, str], doc_id: str, output_dir: str, out: TextIO, backend_name: str | None) -> int:
    backend, adapter, token, early_exit = _load_backend_adapter(env, out, backend_name)
    if early_exit is not None:
        return early_exit
    assert backend is not None and adapter is not None and token is not None
    result = adapter.download_document(doc_id=doc_id)  # type: ignore[attr-defined]
    return _write_downloaded_document(result, output_dir, out, _token_source(backend.name), principal=token.principal)


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    out: TextIO | None = None,
) -> int:
    output = out or sys.stdout
    parser = build_parser()
    if argv in (["--help"], ["-h"]):
        parser.print_help(output)
        return 0
    try:
        with redirect_stdout(output):
            args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if args.version:
        output.write(f"mcp-docs {__version__}\n")
        return 0
    current_env = os.environ if env is None else env
    backend_name = getattr(args, "backend", None)

    if args.command is None:
        parser.print_help(output)
        return 0

    if args.command == "backends":
        return _handle_backends(output)

    if args.command == "info":
        return _handle_info(current_env, output, backend_name)

    if args.command == "login":
        if args.check:
            return _handle_login_check(current_env, output, backend_name)
        return _not_implemented("login", output, backend_name)

    if args.command == "list-folders":
        if args.mock:
            return _handle_mock_list_folders(args.root, args.cursor, args.page_size, output, backend_name)
        return _handle_list_folders(current_env, args.root, args.cursor, args.page_size, output, backend_name)

    if args.command == "list-docs":
        if args.mock:
            return _handle_mock_list_docs(args.folder, args.cursor, args.page_size, output, backend_name)
        return _handle_list_docs(current_env, args.folder, args.cursor, args.page_size, output, backend_name)

    if args.command == "search":
        if args.mock:
            return _handle_mock_search(args.query, args.limit, output, backend_name)
        return _handle_search(current_env, args.query, args.limit, output, backend_name)

    if args.command == "download":
        if args.mock:
            return _handle_mock_download(args.doc_id, args.output, output, backend_name)
        return _handle_download(current_env, args.doc_id, args.output, output, backend_name)

    return _not_implemented("unknown", output, backend_name)


if __name__ == "__main__":
    raise SystemExit(main())
