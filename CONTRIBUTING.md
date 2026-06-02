# Contributing

Thank you for helping improve `mcp-docs-toolkit`.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pytest
```

Run the test suite:

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_mock_server.py
```

## Development Rules

- Keep runtime code standard-library only unless a dependency is clearly justified.
- Keep public examples generic and runnable with mock data.
- Do not commit credentials, tokens, cookies, downloaded private documents, or real service URLs.
- Do not commit real values for `MCP_DOCS_CLIENT_SECRET` or `MCP_DOCS_PASSWORD`.
- Prefer tests that inject fake openers or use the local mock server.
- Keep CLI output as normalized JSON with `ok`, `stage`, `auth`, `data`, and `error`.

## Before Opening A Pull Request

Run:

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_mock_server.py
git diff --check
```

Run the sensitive-content scan from `docs/open-source-sanitization.md` before sharing a branch publicly.
