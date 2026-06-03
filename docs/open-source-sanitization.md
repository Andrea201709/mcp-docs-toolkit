# Open Source Sanitization

This repository is designed to be public and generic. Run these checks before publishing, tagging a release, or submitting the project for review.

## Final Sensitive-Content Scan

```bash
pattern="$(printf '%s|' 'ho''wbuy' 'C''RM' '客''户收益' '高''端收益' '投''顾客户号' '内''网' '真''实接口' | sed 's/|$//')"
rg -n "$pattern" . --glob '!.venv/**' --glob '!docs/superpowers/plans/**' || true
```

Expected result: no output.

## Incomplete Marker Scan

```bash
pattern="$(printf '%s|' 'TB''D' 'TO''DO' 'FIX''ME' | sed 's/|$//')"
rg -n "$pattern" src tests README.md examples docs --glob '!docs/superpowers/plans/**' || true
```

Expected result: no output.

## Manual Checklist

- No real credentials, tokens, cookies, or authorization headers.
- No real service URLs, private document paths, or production API routes.
- No downloaded documents or user data.
- Mock examples still run with `--mock`.
- `docs/security.md` reflects current credential and privacy behavior.
- `docs/codex-oss-application.md` reflects the submitted public project summary and does not claim approval.
