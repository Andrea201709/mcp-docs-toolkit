# GitHub Release Checklist

Use this checklist before making the repository public, sharing it for review, or submitting the Codex for Open Source application. The current path is GitHub-only. TestPyPI and PyPI are optional later steps, not required for this release.

## Repository Setup

- Create a public GitHub repository named `mcp-docs-toolkit`.
- Confirm `docs/codex-oss-application.md` lists the final GitHub username, public repository URL, maintainer role, and current application status.
- Keep the default branch clean and avoid committing local downloads, virtual environments, caches, or private documents.
- Confirm `.github/workflows/test.yml` is present so GitHub Actions can run tests on push and pull requests.
- Keep internal planning files out of the public repository. `docs/superpowers/` is ignored and should remain in a private archive if needed.
- Push only the clean public branch, for example `git push -u origin public-main:main`. Do not push all branches or the private development branch history.

## Local Verification

Run the full test suite:

```bash
PYTHONPATH=src:examples pytest tests/ -v --ignore=tests/test_mock_server.py
```

Check whitespace and patch hygiene:

```bash
git diff --check
```

Run the final sensitive-content scan:

```bash
pattern="$(printf '%s|' 'ho''wbuy' 'C''RM' '客''户收益' '高''端收益' '投''顾客户号' '内''网' '真''实接口' | sed 's/|$//')"
rg -n "$pattern" . --glob '!.venv/**' --glob '!docs/superpowers/plans/**' || true
```

Expected result: no output.

## Documentation Review

- README explains editable local setup, GitHub installation, mock commands, backend selection, config inspection, security, and contribution guidance.
- `docs/security.md` explains credentials, privacy boundaries, download behavior, and security reporting.
- `docs/open-source-sanitization.md` contains the final scan commands.
- `docs/codex-oss-application.md` reflects the submitted public project summary and does not claim approval.
- `examples/.env.example` uses placeholders only.
- `examples/codex-skill-template/SKILL.md` documents all supported backends.

## Manual Reviewer Items

- Confirm the public repository URL is `https://github.com/Andrea201709/mcp-docs-toolkit`.
- Confirm the GitHub username is `Andrea201709` and maintainer role is `creator and maintainer`.
- Keep the Codex for Open Source application notes aligned with the public repository status.

## Optional Later Packaging

Do not publish to TestPyPI or PyPI as part of this GitHub-only release. If the project later needs package-index installation, add package URLs, build verification, TestPyPI upload notes, and PyPI release steps in a separate maintainer-approved batch.
