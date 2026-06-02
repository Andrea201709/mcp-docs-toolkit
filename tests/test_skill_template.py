from pathlib import Path


SKILL_PATH = Path("examples/codex-skill-template/SKILL.md")
KEYCLOAK_ENV_VARS = {
    "MCP_DOCS_KEYCLOAK_URL",
    "MCP_DOCS_KEYCLOAK_REALM",
    "MCP_DOCS_CLIENT_ID",
    "MCP_DOCS_CLIENT_SECRET",
    "MCP_DOCS_USERNAME",
    "MCP_DOCS_PASSWORD",
    "MCP_DOCS_API_URL",
}
NOTION_ENV_VARS = {"MCP_DOCS_NOTION_TOKEN"}
CONFLUENCE_ENV_VARS = {
    "MCP_DOCS_CONFLUENCE_URL",
    "MCP_DOCS_CONFLUENCE_EMAIL",
    "MCP_DOCS_CONFLUENCE_API_TOKEN",
}
GOOGLE_DRIVE_ENV_VARS = {"MCP_DOCS_GOOGLE_ACCESS_TOKEN"}
ALL_ENV_VARS = KEYCLOAK_ENV_VARS | NOTION_ENV_VARS | CONFLUENCE_ENV_VARS | GOOGLE_DRIVE_ENV_VARS
PRIVATE_TERMS = (
    "ho" + "wbuy",
    "C" + "RM",
    "客" + "户收益",
    "高" + "端收益",
    "投" + "顾客户号",
    "内" + "网",
    "真" + "实接口",
)


def read_skill():
    return SKILL_PATH.read_text(encoding="utf-8")


def frontmatter(text):
    assert text.startswith("---\n")
    return text.split("---", 2)[1]


def frontmatter_fields(text):
    fields = {}
    for line in frontmatter(text).strip().splitlines():
        key, separator, value = line.partition(":")
        assert separator == ":"
        fields[key.strip()] = value.strip()
    return fields


def test_skill_template_has_valid_frontmatter():
    text = read_skill()
    fields = frontmatter_fields(text)

    assert fields["name"] == "mcp-docs-toolkit"
    assert fields["description"].startswith("Use when")
    assert len(frontmatter(text)) < 1024


def test_skill_template_explains_when_to_use_toolkit():
    text = read_skill()

    assert "When to Use" in text
    assert "mcp-docs" in text
    assert "Backend Selection" in text


def test_skill_template_documents_all_backends():
    text = read_skill()

    for backend in ("keycloak", "notion", "confluence", "google-drive"):
        assert f"--backend {backend}" in text


def test_skill_template_uses_environment_variables_for_credentials_only():
    text = read_skill()

    for name in ALL_ENV_VARS:
        assert name in text
    assert "Never pass credentials as command arguments" in text
    assert "--password" not in text
    assert "--client-secret" not in text
    assert "example-password" not in text
    assert "example-secret" not in text


def test_skill_template_documents_cli_commands_and_normalized_json():
    text = read_skill()

    assert "mcp-docs list-folders" in text
    assert "mcp-docs list-docs" in text
    assert "mcp-docs download" in text
    assert "mcp-docs backends" in text
    assert "normalized JSON" in text
    for key in ('"ok"', '"stage"', '"auth"', '"data"', '"error"'):
        assert key in text


def test_skill_template_contains_no_private_terms():
    text = read_skill()

    for term in PRIVATE_TERMS:
        assert term not in text
