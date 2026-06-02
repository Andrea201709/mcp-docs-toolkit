from mcp_docs_toolkit.models import AccessToken, DownloadedDocument, Folder, ToolError


def test_access_token_repr_hides_token_value():
    token = AccessToken(value="secret-token", expires_in=300, token_type="Bearer", principal="user@example.com")

    rendered = repr(token)

    assert "secret-token" not in rendered
    assert "user@example.com" in rendered


def test_downloaded_document_repr_hides_content_bytes():
    document = DownloadedDocument(filename="Example.pdf", content=b"secret bytes", mime_type="application/pdf")

    rendered = repr(document)

    assert "secret bytes" not in rendered
    assert "Example.pdf" in rendered


def test_folder_to_dict_uses_public_parent_id_key():
    folder = Folder(id="F001", name="Example Folder", parent_id=None)

    assert folder.to_dict() == {"id": "F001", "name": "Example Folder", "parentId": None}


def test_tool_error_to_dict():
    error = ToolError(code="NETWORK_ERROR", message="Connection failed.", retryable=True)

    assert error.to_dict() == {
        "code": "NETWORK_ERROR",
        "message": "Connection failed.",
        "retryable": True,
    }
