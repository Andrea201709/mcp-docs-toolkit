# Security

## Credential Handling

`mcp-docs-toolkit` reads credentials from environment variables. Do not pass passwords, client secrets, tokens, cookies, or authorization headers as command-line arguments.

Required variables for real endpoints depend on the selected backend.

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

The CLI redacts known secret values from structured output and error messages. Tests cover raw and URL-encoded credential values.

## Privacy Boundary

The repository contains only public mock data. It must not include real hostnames, real identities, private document text, downloaded files, or production API paths.

The mock server is for local demos and tests. It is not an authentication server, policy engine, or storage service.

## Downloaded Documents

Downloaded files are written only to the requested output directory. The CLI rejects unsafe filenames that are empty, absolute, nested, or contain parent-directory traversal.

Do not commit downloaded documents. Add local output folders to your own ignored files if needed.

## Reporting Security Issues

Until the project has a public security contact, report issues privately to the project maintainer. Do not open public issues that include credentials, tokens, private document content, or exploit details.
