---
name: mcp-docs-toolkit
description: Use when a user needs to find, list, or download documents through the mcp-docs CLI. Supports Keycloak, Notion, Confluence, and Google Drive backends.
---

# MCP Docs Toolkit

## When to Use

Use this skill when the user asks to work with authorized documents through `mcp-docs`, including:

- checking whether document API access is configured;
- listing accessible folders or spaces;
- listing documents in a folder, page, or space;
- searching documents in built-in mock data;
- downloading a document by id;
- running a local mock demo before configuring real endpoints.

Do not use this skill for unrelated file search, browser scraping, or direct credential handling.

## Backend Selection

The CLI supports multiple document backends. Use `--backend <name>` to select one. If omitted, `keycloak` is the default.

Non-mock commands route through the selected backend adapter after configuration validation and authentication. Use mock commands for examples unless the user has already configured the backend's environment variables.

Available backends and their use cases:

| Backend | Flag | When to use |
|---|---|---|
| keycloak | `--backend keycloak` | Keycloak-protected document APIs (OAuth2 password grant) |
| notion | `--backend notion` | Notion pages and databases (API token) |
| confluence | `--backend confluence` | Confluence spaces and pages (Basic auth) |
| google-drive | `--backend google-drive` | Google Drive files and folders (OAuth2 Bearer token) |

To list backends programmatically:

```bash
mcp-docs backends
```

## Credential Boundary

Read credentials from environment variables only. Each backend has its own set:

**Keycloak:**

- `MCP_DOCS_KEYCLOAK_URL`
- `MCP_DOCS_KEYCLOAK_REALM`
- `MCP_DOCS_CLIENT_ID`
- `MCP_DOCS_CLIENT_SECRET`
- `MCP_DOCS_USERNAME`
- `MCP_DOCS_PASSWORD`
- `MCP_DOCS_API_URL`

**Notion:**

- `MCP_DOCS_NOTION_TOKEN`

**Confluence:**

- `MCP_DOCS_CONFLUENCE_URL`
- `MCP_DOCS_CONFLUENCE_EMAIL`
- `MCP_DOCS_CONFLUENCE_API_TOKEN`

**Google Drive:**

- `MCP_DOCS_GOOGLE_ACCESS_TOKEN`

Never pass credentials as command arguments. Never echo, log, summarize, or store token, password, cookie, client secret, or authorization header values.

## Commands

### Check Configuration

```bash
mcp-docs login --check
mcp-docs --backend notion login --check
mcp-docs --backend confluence login --check
mcp-docs --backend google-drive login --check
```

### List Folders

```bash
mcp-docs list-folders
mcp-docs list-folders --page-size 50
mcp-docs --backend notion list-folders
mcp-docs --backend confluence list-folders
mcp-docs --backend google-drive list-folders
```

### List Documents

```bash
mcp-docs list-docs --folder F001
mcp-docs list-docs --folder F001 --page-size 50 --cursor 50
mcp-docs --backend notion list-docs --folder page-001
mcp-docs --backend confluence list-docs --folder space-001
mcp-docs --backend google-drive list-docs --folder folder-001
```

### Search Documents

```bash
mcp-docs search --query example --mock
mcp-docs --backend notion search --query project --mock
mcp-docs --backend confluence search --query api --mock
mcp-docs --backend google-drive search --query report --mock
```

### Download a Document

```bash
mcp-docs download --doc-id D001 --output ./downloads
mcp-docs --backend notion download --doc-id block-001 --output ./downloads
mcp-docs --backend confluence download --doc-id page-001 --output ./downloads
mcp-docs --backend google-drive download --doc-id file-001 --output ./downloads
```

### Mock Mode (no credentials needed)

Any command can use `--mock` to run against built-in public data:

```bash
mcp-docs list-folders --mock
mcp-docs list-folders --mock --page-size 1
mcp-docs search --mock --query example
mcp-docs --backend notion list-folders --mock
mcp-docs --backend confluence list-docs --mock --folder space-001
mcp-docs --backend google-drive download --mock --doc-id file-001 --output ./downloads
```

## Output Handling

Return the CLI response as normalized JSON. Preserve the envelope and do not omit fields:

```json
{
  "ok": true,
  "stage": "list_folders",
  "auth": {
    "tokenSource": "NOTION",
    "principal": "notion-user"
  },
  "data": {},
  "error": null
}
```

The `tokenSource` field reflects the active backend (e.g. `KEYCLOAK`, `NOTION`, `CONFLUENCE`, `GOOGLE_DRIVE`).

When `"ok"` is `false`, report the `"error"` object exactly enough for the user to act on it. Do not invent success if the CLI returns an error.

## Safety Checks

Before sharing output with the user:

- confirm no token, password, cookie, client secret, or authorization header value appears in the response;
- keep downloaded files in the requested output directory;
- use `--mock` for examples unless the user has already configured real environment variables;
- verify the correct `--backend` flag is being used for the user's document system.
