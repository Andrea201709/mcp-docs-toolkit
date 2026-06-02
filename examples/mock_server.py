"""Local mock server for the public mcp-docs-toolkit API contract."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from mcp_docs_toolkit.mock_data import (
    MOCK_ACCESS_TOKEN,
    MOCK_CLIENT_ID,
    MOCK_CLIENT_SECRET,
    MOCK_DOCUMENT_CONTENT,
    MOCK_DOCUMENTS,
    MOCK_FOLDERS,
    MOCK_PASSWORD,
    MOCK_REALM,
    MOCK_USERNAME,
)


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _form_or_json(body: bytes) -> dict[str, object]:
    try:
        parsed = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {key: values[0] for key, values in parse_qs(body.decode("utf-8")).items()}
    return parsed if isinstance(parsed, dict) else {}


def create_app_handler():
    class MockDocsHandler(BaseHTTPRequestHandler):
        server_version = "mcp-docs-mock/0.1"

        def log_message(self, format, *args):  # noqa: A002
            return

        def _read_payload(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0"))
            return _form_or_json(self.rfile.read(length))

        def _write(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
            self.send_response(status)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_json(self, status: int, payload: dict[str, object]) -> None:
            self._write(status, _json_bytes(payload), {"Content-Type": "application/json"})

        def _authorized(self) -> bool:
            return self.headers.get("Authorization") == f"Bearer {MOCK_ACCESS_TOKEN}"

        def do_POST(self) -> None:
            if self.path == f"/realms/{MOCK_REALM}/protocol/openid-connect/token":
                self._handle_token()
                return
            if not self._authorized():
                self._write_json(401, {"error": "unauthorized"})
                return
            if self.path == "/folders/list":
                self._handle_folders()
                return
            if self.path == "/documents/list":
                self._handle_documents()
                return
            if self.path == "/documents/download":
                self._handle_download()
                return
            self._write_json(404, {"error": "not_found"})

        def _handle_token(self) -> None:
            payload = self._read_payload()
            if (
                payload.get("client_id") != MOCK_CLIENT_ID
                or payload.get("client_secret") != MOCK_CLIENT_SECRET
                or payload.get("username") != MOCK_USERNAME
                or payload.get("password") != MOCK_PASSWORD
            ):
                self._write_json(401, {"error": "invalid_grant"})
                return
            self._write_json(
                200,
                {
                    "access_token": MOCK_ACCESS_TOKEN,
                    "expires_in": 300,
                    "token_type": "Bearer",
                },
            )

        def _handle_folders(self) -> None:
            payload = self._read_payload()
            root_id = payload.get("rootFolderId")
            folders = MOCK_FOLDERS if root_id in (None, "", "ROOT") else []
            self._write_json(200, {"folders": folders})

        def _handle_documents(self) -> None:
            payload = self._read_payload()
            folder_id = payload.get("folderId")
            documents = [document for document in MOCK_DOCUMENTS if document["folderId"] == folder_id]
            self._write_json(200, {"documents": documents})

        def _handle_download(self) -> None:
            payload = self._read_payload()
            doc_id = payload.get("docId")
            document = next((item for item in MOCK_DOCUMENTS if item["id"] == doc_id), None)
            if document is None:
                self._write_json(404, {"error": "not_found"})
                return
            self._write(
                200,
                MOCK_DOCUMENT_CONTENT,
                {
                    "Content-Type": str(document["mimeType"]),
                    "Content-Disposition": f'attachment; filename="{document["name"]}"',
                },
            )

    return MockDocsHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the mcp-docs-toolkit local mock server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), create_app_handler())
    print(f"mcp-docs mock server listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
