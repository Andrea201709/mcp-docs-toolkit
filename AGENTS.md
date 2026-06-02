# AGENTS.md — Guide for AI Coding Agents

This document helps Codex, Claude, and other AI agents understand the project structure, conventions, and how to extend it.

## Project Overview

`mcp-docs-toolkit` is a Python CLI and toolkit for connecting document APIs to local developer and AI agent workflows. It provides a pluggable adapter architecture with credential-free mock demos for multiple backend shapes.

Current public demos use `--mock`. Non-mock commands route through the selected backend adapter. Real network execution for public backends remains experimental until each backend has request-shape and response-normalization tests with fake transport.

## Directory Structure

```
src/mcp_docs_toolkit/
    adapters/                  # Pluggable backend system (the extension point)
        base.py                # Protocol definitions: AuthAdapter, DocAdapter, BackendFactory
        registry.py            # Backend registry: register_backend(), get_backend(), available_backends()
        keycloak/              # Keycloak backend (original, OAuth2 password grant)
        notion/                # Notion backend (Bearer token auth)
        confluence/            # Confluence backend (Basic auth)
        google_drive/          # Google Drive backend (OAuth2 Bearer token)
    auth.py                    # Backward-compatible Keycloak auth shim
    client.py                  # Backward-compatible Keycloak DocumentApiClient shim
    config.py                  # Backward-compatible Keycloak Settings shim
    cli.py                     # CLI entry point with --backend flag
    models.py                  # Shared data models: Folder, Document, AccessToken, ApiResult, etc.
    output.py                  # JSON output helpers: success_response(), error_response(), to_json()
    errors.py                  # Error code constants
    redaction.py               # Secret redaction utilities
    mock_data.py               # Shared mock data (Keycloak format)

tests/
    test_adapters_registry.py  # Registry and cross-backend CLI tests
    test_adapters_notion.py    # Notion adapter tests
    test_adapters_confluence.py
    test_adapters_google_drive.py
    test_cli.py                # CLI tests, including default Keycloak compatibility
    test_auth.py, test_client.py, test_config.py, etc.  # Keycloak compatibility unit tests
```

## Conventions

- All Python files start with `from __future__ import annotations`.
- Standard library only (no third-party runtime dependencies).
- CLI output is always normalized JSON with `ok`, `stage`, `auth`, `data`, `error` fields.
- Credentials are read from environment variables only, never from command arguments.
- Mock adapters return the same JSON shape as real adapters (no network, no credentials).
- Tests use pytest. Run with: `PYTHONPATH=src:examples pytest tests/ -v --ignore=tests/test_mock_server.py`

## How to Add a New Backend

1. Create `src/mcp_docs_toolkit/adapters/<name>/` with:
   - `config.py` — config dataclass and `load_<name>_config()` function returning `ConfigResult`
   - `adapter.py` — `<Name>AuthAdapter`, `<Name>DocAdapter`, `<Name>BackendFactory`
   - `mock.py` — `<Name>MockDocAdapter` with hardcoded public data
   - `__init__.py` — import factory and call `register_backend(<Name>BackendFactory())`

2. The `BackendFactory` must implement:
   - `name: str` — unique backend identifier (used in `--backend` flag)
   - `required_env_vars: Sequence[str]`
   - `load_config(env) -> ConfigResult`
   - `create_auth(config) -> AuthAdapter`
   - `create_doc_adapter(config, token) -> DocAdapter`
   - `create_mock_doc_adapter() -> DocAdapter`

3. Add tests in `tests/test_adapters_<name>.py` covering config, auth, mock adapter, and CLI integration.

4. Add the backend package to `_ensure_loaded()` in `registry.py`. The registry uses explicit imports so startup stays predictable and standard-library only.

## Key Interfaces

### DocAdapter Protocol
```python
class DocAdapter(Protocol):
    def list_folders(self, root_id: str | None = None, page_cursor: str | None = None, page_size: int = 100) -> ApiResult: ...
    def list_documents(self, folder_id: str, page_cursor: str | None = None, page_size: int = 100) -> ApiResult: ...
    def download_document(self, doc_id: str) -> ApiResult: ...
    def search_documents(self, query: str, limit: int = 10) -> ApiResult: ...
```

### AuthAdapter Protocol
```python
class AuthAdapter(Protocol):
    def authenticate(self) -> AuthResult: ...
```

## Common Commands

- **Run all tests**: `PYTHONPATH=src:examples pytest tests/ -v --ignore=tests/test_mock_server.py`
- **Run mock CLI**: `PYTHONPATH=src python3 -m mcp_docs_toolkit.cli --backend notion list-folders --mock`
- **Run paginated mock CLI**: `PYTHONPATH=src python3 -m mcp_docs_toolkit.cli --backend notion list-folders --mock --page-size 1`
- **Search mock data**: `PYTHONPATH=src python3 -m mcp_docs_toolkit.cli --backend confluence search --query api --mock`
- **List backends**: `PYTHONPATH=src python3 -m mcp_docs_toolkit.cli backends`
- **Inspect backend config needs**: `PYTHONPATH=src python3 -m mcp_docs_toolkit.cli --backend notion info`
- **Check config**: `PYTHONPATH=src python3 -m mcp_docs_toolkit.cli --backend confluence login --check`

## Completed Foundation

- Multi-backend registry and adapter directories exist for Keycloak, Notion, Confluence, and Google Drive.
- Mock CLI demos work for every backend.
- `mcp-docs search --mock` searches built-in public mock data across backend-specific document shapes.
- `list-folders --mock` and `list-docs --mock` support `--cursor` and `--page-size`.
- `mcp-docs info` reports required environment variables without revealing values.
- Non-mock commands load backend config, authenticate, and call the selected adapter.
- Missing config errors list required variables without revealing values.
- Notion, Confluence, and Google Drive real adapters have fake-transport tests for request shape, response normalization, and 401 auth error normalization.
- Keycloak legacy implementations live under `adapters/keycloak/`; top-level `auth.py`, `client.py`, `config.py`, and `mock_transport.py` are backward-compatible shims.
- GitHub Actions CI runs tests on Python 3.10, 3.11, and 3.12.

## Pending Tasks

Tasks are ordered by priority. Each task includes acceptance criteria. Pick the first unblocked task and work through it.

### Task 1: Prepare GitHub OSS Release

Prepare the repository for a GitHub-only public open-source release. Do not publish to TestPyPI, PyPI, or any external platform without maintainer approval.

**Acceptance criteria:**
- README includes GitHub installation instructions and mock quickstart.
- `docs/github-release-checklist.md` covers public repo setup, tests, sanitization, and manual reviewer steps.
- `docs/codex-oss-application.md` uses the current multi-backend project description.
- PyPI/TestPyPI are documented as optional later steps, not required for this release.
- Full tests, `git diff --check`, and sensitive-content scan pass.
