# Multi-Backend Architecture

Status: implemented foundation.

## Goal

`mcp-docs-toolkit` is now a pluggable multi-backend document toolkit. Keycloak, Notion, Confluence, and Google Drive backend packages live under `src/mcp_docs_toolkit/adapters/`.

## Architecture

### Adapter Protocols (src/mcp_docs_toolkit/adapters/base.py)

```python
class AuthAdapter(Protocol):
    """Each backend implements its own authentication."""
    def authenticate(self) -> AuthResult: ...

class DocAdapter(Protocol):
    """Uniform interface for document operations."""
    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult: ...
    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult: ...
    def download_document(self, doc_id: str) -> ApiResult: ...
    def search_documents(self, query: str, limit: int = 10) -> ApiResult: ...

class BackendFactory(Protocol):
    """Creates auth + doc adapters from env vars."""
    name: str
    required_env_vars: tuple[str, ...]
    def load_config(self, env: Mapping[str, str]) -> ConfigResult: ...
    def create_auth(self, config: Any) -> AuthAdapter: ...
    def create_doc_adapter(self, config: Any, token: AccessToken) -> DocAdapter: ...
```

### Registry (src/mcp_docs_toolkit/adapters/registry.py)

- `BACKENDS: dict[str, BackendFactory]` maps backend name to factory
- `get_backend(name: str) -> BackendFactory` lookup function
- Auto-discovers adapter modules via explicit imports

### File Structure

```
src/mcp_docs_toolkit/
  adapters/
    __init__.py          # exports registry, protocols
    base.py              # AuthAdapter, DocAdapter, BackendFactory protocols
    registry.py          # BACKENDS dict, get_backend()
    keycloak/
      __init__.py
      adapter.py         # KeycloakBackendFactory + KeycloakDocAdapter
      auth.py            # adapter auth wrapper
      config.py          # KeycloakSettings, load_keycloak_config()
      mock.py            # Keycloak mock adapter
      _auth.py           # internal compatibility implementation
      _client.py         # internal compatibility implementation
      _config_compat.py  # internal compatibility implementation
      _mock_transport.py # internal compatibility implementation
    notion/
      __init__.py
      adapter.py
      config.py
      mock.py
    confluence/
      __init__.py
      adapter.py
      config.py
      mock.py
    google_drive/
      __init__.py
      adapter.py
      config.py
      mock.py
```

### What Stays Unchanged

- `models.py` - Folder, Document, DownloadedDocument, AuthResult, ApiResult, ToolError are generic
- `output.py` - success_response, error_response, to_json
- `redaction.py` - redact_values
- `errors.py` - error codes
- `mock_data.py` - stays as shared mock data (MOCK_FOLDERS, MOCK_DOCUMENTS, etc.)

### Compatibility Surface

- `config.py` re-exports Keycloak compatibility settings from `adapters/keycloak/_config_compat.py`
- `auth.py` re-exports Keycloak compatibility auth helpers from `adapters/keycloak/_auth.py`
- `client.py` re-exports Keycloak compatibility client helpers from `adapters/keycloak/_client.py`
- `mock_transport.py` re-exports Keycloak compatibility mock transport from `adapters/keycloak/_mock_transport.py`
- `cli.py` exposes `--backend`, defaulting to `keycloak` for backward-compatible usage

### CLI Usage (backward compatible)

```bash
# Existing - still works, uses keycloak backend by default
mcp-docs list-folders --mock
mcp-docs list-docs --mock --folder F001

# New - explicit backend selection
mcp-docs --backend notion list-folders --mock
mcp-docs --backend confluence list-docs --mock --folder space-001
mcp-docs --backend google-drive list-docs --mock --folder folder-001

# List available backends
mcp-docs backends
```

## Implemented Foundation

- `adapters/base.py` defines the shared protocols.
- `adapters/registry.py` registers backend factories through explicit imports.
- Keycloak remains the default backend for backward-compatible CLI usage.
- Notion, Confluence, and Google Drive have mock adapters and non-mock fake-transport coverage.
- Mock pagination and mock search are available through the CLI.
- Top-level `auth.py`, `client.py`, `config.py`, and `mock_transport.py` are backward-compatible Keycloak shims.

## Codex Compatibility Notes

- Each adapter is self-contained in its own directory
- Codex can add new adapters by following the pattern in adapters/keycloak/
- BackendFactory protocol is the contract; implement it and register
- Mock data is per-adapter, making tests independent
- CLI uses registry pattern, no hardcoded backend logic
