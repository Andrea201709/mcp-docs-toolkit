# Mock API Contract

This document describes the public mock API contract used by `mcp-docs-toolkit`. It is intentionally generic and does not claim compatibility with any private service.

## Token Endpoint

```text
POST /realms/{realm}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded
```

Request fields:

- `grant_type`
- `client_id`
- `client_secret`
- `username`
- `password`
- `scope`

Response fields:

- `access_token`
- `expires_in`
- `token_type`

## Folder Endpoint

```text
POST /folders/list
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "rootFolderId": "ROOT"
}
```

Response:

```json
{
  "folders": [
    {
      "id": "F001",
      "name": "Example Folder",
      "parentId": null
    }
  ]
}
```

## Document Endpoint

```text
POST /documents/list
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "folderId": "F001"
}
```

Response:

```json
{
  "documents": [
    {
      "id": "D001",
      "name": "Example Document.pdf",
      "folderId": "F001",
      "mimeType": "application/pdf",
      "size": 29
    }
  ]
}
```

## Download Endpoint

```text
POST /documents/download
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "docId": "D001"
}
```

Response body: document bytes.

Response headers:

- `Content-Type`
- `Content-Disposition`
