# Codex Instructions

Copy-paste the prompts below into Codex to execute remaining tasks. Run them in order.

Current foundation already includes multi-backend mock/config support, mock pagination, `mcp-docs search --mock`, `mcp-docs info`, non-mock CLI routing through adapters, public-backend fake-transport coverage, Keycloak legacy implementation consolidation, and GitHub Actions CI.

---

## Prompt 0: Project Onboarding

```
Read AGENTS.md in the project root. This is your guide to the codebase.

Then run the test suite to confirm the project is in a healthy state:

    PYTHONPATH=src:examples pytest tests/ -v --ignore=tests/test_mock_server.py

Report: how many tests pass, how many fail. Do not proceed if any test fails.
```

---

## Prompt 1: Prepare GitHub OSS Release

```
Read AGENTS.md, then complete Task 1 ("Prepare GitHub OSS Release").

Do not publish to TestPyPI, PyPI, or any external platform without explicit maintainer approval.

Steps:
1. Review README.md and ensure GitHub installation plus mock quickstart are clear.
2. Review docs/github-release-checklist.md and keep PyPI/TestPyPI marked optional.
3. Review docs/codex-oss-application.md and ensure it describes the current multi-backend project.
4. Run the full test suite and documentation checks.
5. Run git diff --check and the sensitive-content scan from docs/open-source-sanitization.md.
6. Report remaining manual items, especially GitHub username, public repository URL, and application-form submission.

Run: PYTHONPATH=src:examples pytest tests/ -v --ignore=tests/test_mock_server.py
```
