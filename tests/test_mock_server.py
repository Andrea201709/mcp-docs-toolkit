import json
from http.server import HTTPServer
from threading import Thread
from urllib.request import ProxyHandler, Request, build_opener

from examples.mock_server import create_app_handler


LOCAL_OPENER = build_opener(ProxyHandler({}))


def start_server():
    server = HTTPServer(("127.0.0.1", 0), create_app_handler())
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def post_json(base_url, path, payload, headers=None):
    request = Request(
        base_url + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with LOCAL_OPENER.open(request, timeout=3) as response:
        return response.read(), response.headers


def test_mock_server_token_endpoint_returns_access_token():
    server = start_server()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        request = Request(
            base_url + "/realms/example-realm/protocol/openid-connect/token",
            data=b"grant_type=password&client_id=docs-cli&client_secret=example-secret&username=user%40example.com&password=example-password",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        with LOCAL_OPENER.open(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))

        assert payload["access_token"] == "mock-access-token"
        assert payload["token_type"] == "Bearer"
    finally:
        server.shutdown()
        server.server_close()


def test_mock_server_lists_folders():
    server = start_server()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        body, _headers = post_json(
            base_url,
            "/folders/list",
            {"rootFolderId": "ROOT"},
            headers={"Authorization": "Bearer mock-access-token"},
        )

        payload = json.loads(body.decode("utf-8"))

        assert payload == {"folders": [{"id": "F001", "name": "Example Folder", "parentId": None}]}
    finally:
        server.shutdown()
        server.server_close()


def test_mock_server_downloads_document():
    server = start_server()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        body, headers = post_json(
            base_url,
            "/documents/download",
            {"docId": "D001"},
            headers={"Authorization": "Bearer mock-access-token"},
        )

        assert body == b"Example mock document bytes.\n"
        assert headers["Content-Type"] == "application/pdf"
        assert headers["Content-Disposition"] == 'attachment; filename="Example Document.pdf"'
    finally:
        server.shutdown()
        server.server_close()
