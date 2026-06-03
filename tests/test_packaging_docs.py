from pathlib import Path


ROOT = Path(".")
PRIVATE_TERMS = (
    "ho" + "wbuy",
    "C" + "RM",
    "客" + "户收益",
    "高" + "端收益",
    "投" + "顾客户号",
    "内" + "网",
    "真" + "实接口",
)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_has_five_minute_quickstart_and_public_sections():
    text = read("README.md")

    assert "5-Minute Quickstart" in text
    assert "Use Python 3.10 or newer" in text
    assert "python3.11 -m venv .venv" in text
    assert ".venv/bin/python -m pip install --upgrade pip setuptools" in text
    assert ".venv/bin/python -m pip install -e ." in text
    assert ".venv/bin/mcp-docs list-folders --mock" in text
    assert ".venv/bin/mcp-docs list-docs --mock --folder F001" in text
    assert ".venv/bin/mcp-docs download --mock --doc-id D001" in text
    assert "examples/codex-skill-template/SKILL.md" in text
    assert "Security" in text
    assert "Contributing" in text
    assert "GitHub Installation" in text
    assert '.venv/bin/python -m pip install "git+https://github.com/Andrea201709/mcp-docs-toolkit.git"' in text


def test_license_is_mit():
    text = read("LICENSE")

    assert "MIT License" in text
    assert "Andrea" in text
    assert "Permission is hereby granted" in text


def test_contributing_documents_tests_and_no_secret_rules():
    text = read("CONTRIBUTING.md")

    assert ".venv/bin/python -m pytest tests/ -v --ignore=tests/test_mock_server.py" in text
    assert "Do not commit credentials" in text
    assert "MCP_DOCS_CLIENT_SECRET" in text
    assert "MCP_DOCS_PASSWORD" in text


def test_security_doc_explains_credentials_privacy_and_reporting():
    text = read("docs/security.md")

    assert "Credential Handling" in text
    assert "Privacy Boundary" in text
    assert "Downloaded Documents" in text
    assert "Reporting Security Issues" in text
    assert "environment variables" in text


def test_sanitization_doc_contains_final_scan_commands():
    text = read("docs/open-source-sanitization.md")

    assert "Final Sensitive-Content Scan" in text
    assert "rg -n" in text
    assert "!.venv/**" in text
    assert "No real credentials" in text
    assert "does not claim approval" in text


def test_codex_oss_application_draft_explains_relevance():
    text = read("docs/codex-oss-application.md")

    assert "Codex for Open Source" in text
    assert "https://openai.com/form/codex-for-oss/" in text
    assert "multi-backend" in text
    assert "Codex workflows" in text
    assert "maintenance automation" in text
    assert "release" in text.lower()
    assert "Andrea201709" in text
    assert "https://github.com/Andrea201709/mcp-docs-toolkit" in text
    assert "creator and maintainer" in text
    assert "submitted" in text.lower()
    assert "not yet submitted" not in text


def test_github_release_checklist_keeps_pypi_optional():
    text = read("docs/github-release-checklist.md")

    assert "GitHub Release Checklist" in text
    assert "GitHub-only" in text
    assert "TestPyPI" in text
    assert "optional" in text.lower()
    assert "Do not publish" in text
    assert "current application status" in text
    assert "does not claim approval" in text


def test_env_example_uses_placeholders_only():
    text = read("examples/.env.example")

    for name in (
        "MCP_DOCS_KEYCLOAK_URL",
        "MCP_DOCS_KEYCLOAK_REALM",
        "MCP_DOCS_CLIENT_ID",
        "MCP_DOCS_CLIENT_SECRET",
        "MCP_DOCS_USERNAME",
        "MCP_DOCS_PASSWORD",
        "MCP_DOCS_API_URL",
    ):
        assert name in text
    assert "<your-client-secret>" in text
    assert "example-secret" not in text
    assert "example-password" not in text
    assert "mock-access-token" not in text


def test_mock_api_contract_documents_public_endpoints():
    text = read("examples/mock_api_contract.md")

    assert "POST /realms/{realm}/protocol/openid-connect/token" in text
    assert "POST /folders/list" in text
    assert "POST /documents/list" in text
    assert "POST /documents/download" in text
    assert "mock-access-token" not in text


def test_public_docs_contain_no_private_terms():
    paths = [
        "README.md",
        "CONTRIBUTING.md",
        "docs/security.md",
        "docs/open-source-sanitization.md",
        "docs/codex-oss-application.md",
        "examples/.env.example",
        "examples/mock_api_contract.md",
        "examples/codex-skill-template/SKILL.md",
    ]

    for path in paths:
        text = read(path)
        for term in PRIVATE_TERMS:
            assert term not in text, f"{term} found in {path}"
