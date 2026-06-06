# mcp-docs-toolkit

`mcp-docs-toolkit` is a CLI and Python toolkit for connecting document APIs to local developer and agent workflows. It provides a pluggable adapter architecture, structured JSON output, and credential-free mock demos for local agent workflows.

Available backend adapters:

- **keycloak** — Keycloak-protected document APIs (OAuth2 password grant)
- **notion** — Notion pages and databases (API token)
- **confluence** — Confluence spaces and pages (Basic auth)
- **google-drive** — Google Drive files and folders (OAuth2 Bearer token)

Current public demos use `--mock`, so contributors can try every backend without credentials or network access. Non-mock commands route through the selected backend adapter, but real external API behavior should be treated as experimental until each backend has request-shape and response-normalization tests with fake transport.

The project is intentionally generic. It does not include private hostnames, private API paths, real user ids, customer data, or downloaded documents.

## 5-Minute Quickstart

Create an isolated environment and install the CLI in editable mode from a local checkout:

Use Python 3.10 or newer. Replace `python3.11` with `python3.10`, `python3.12`, or another Python 3.10+ executable if needed.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools
.venv/bin/python -m pip install -e ".[dev]"
```

Run the built-in mock demo without external credentials:

```bash
.venv/bin/mcp-docs list-folders --mock
.venv/bin/mcp-docs list-docs --mock --folder F001
.venv/bin/mcp-docs list-docs --mock --folder F001 --page-size 1
.venv/bin/mcp-docs search --mock --query example
.venv/bin/mcp-docs download --mock --doc-id D001 --output ./downloads
```

Run the test suite:

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_mock_server.py
```

## GitHub Installation

For the current experimental open-source release, install directly from the public GitHub repository:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools
.venv/bin/python -m pip install "git+https://github.com/Andrea201709/mcp-docs-toolkit.git"
.venv/bin/mcp-docs backends
.venv/bin/mcp-docs list-folders --mock
```

PyPI/TestPyPI publishing is optional and not required for trying the project, reviewing the code, or submitting the repository for open-source program review.

Try other backends:

```bash
.venv/bin/mcp-docs --backend notion list-folders --mock
.venv/bin/mcp-docs --backend notion list-folders --mock --page-size 1
.venv/bin/mcp-docs --backend confluence list-docs --mock --folder space-001
.venv/bin/mcp-docs --backend confluence search --mock --query api
.venv/bin/mcp-docs --backend google-drive download --mock --doc-id file-001 --output ./downloads
```

List all available backends:

```bash
.venv/bin/mcp-docs backends
```

The commands return normalized JSON with this envelope:

```json
{
  "ok": true,
  "stage": "list_folders",
  "auth": {
    "tokenSource": "KEYCLOAK",
    "principal": "user@example.com"
  },
  "data": {},
  "error": null
}
```

Run the standalone local mock server:

```bash
PYTHONPATH=src python3 examples/mock_server.py --host 127.0.0.1 --port 8765
```

## Configuration

For real endpoints, configure credentials through environment variables only. Each backend has its own set of variables:

**Keycloak:**

```bash
export MCP_DOCS_KEYCLOAK_URL="<your-keycloak-url>"
export MCP_DOCS_KEYCLOAK_REALM="<your-realm>"
export MCP_DOCS_CLIENT_ID="<your-client-id>"
export MCP_DOCS_CLIENT_SECRET="<your-client-secret>"
export MCP_DOCS_USERNAME="<your-username>"
export MCP_DOCS_PASSWORD="<your-password>"
export MCP_DOCS_API_URL="<your-document-api-url>"
```

**Notion:**

```bash
export MCP_DOCS_NOTION_TOKEN="<your-notion-integration-token>"
```

**Confluence:**

```bash
export MCP_DOCS_CONFLUENCE_URL="<your-confluence-url>"
export MCP_DOCS_CONFLUENCE_EMAIL="<your-email>"
export MCP_DOCS_CONFLUENCE_API_TOKEN="<your-api-token>"
```

**Google Drive:**

```bash
export MCP_DOCS_GOOGLE_ACCESS_TOKEN="<your-oauth2-access-token>"
```

Check configuration without making a network call:

```bash
.venv/bin/mcp-docs login --check
.venv/bin/mcp-docs --backend notion login --check
```

Inspect required variables without revealing values:

```bash
.venv/bin/mcp-docs info
.venv/bin/mcp-docs --backend google-drive info
```

## Real Adapter Coverage

Non-mock adapter paths are covered with fake transport tests, not real credentials:

- Notion: search request shape, response normalization, and 401 auth error normalization
- Confluence: page listing request shape, response normalization, and 401 auth error normalization
- Google Drive: file listing request shape, response normalization, and 401 auth error normalization

## Adding a New Backend

See `AGENTS.md` for the full guide. In short: create `src/mcp_docs_toolkit/adapters/<name>/` with `config.py`, `adapter.py`, `mock.py`, and `__init__.py`, register via `register_backend()`, and add the backend package to the registry loader.

## Codex Skill Template

A copyable Codex skill example is available at `examples/codex-skill-template/SKILL.md`. It shows how an agent can call `mcp-docs`, rely on environment variables for credentials, and preserve normalized JSON output.

## Security

See `docs/security.md` for credential handling, privacy boundaries, download behavior, and reporting guidance.

## Contributing

See `CONTRIBUTING.md` for local setup, tests, documentation checks, and no-secret contribution rules.

## GitHub Release Readiness

See `docs/github-release-checklist.md` before making the repository public or sharing it for review.

## License

MIT. See `LICENSE`.
