from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).parent.parent
SKILL_MD = REPO_ROOT / ".claude" / "skills" / "code-review" / "SKILL.md"
SCHEMAS = REPO_ROOT / "schemas"
CAPABILITIES_SCHEMA = SCHEMAS / "capabilities.json"
REQUEST_SCHEMA = SCHEMAS / "review-request.json"
RESPONSE_SCHEMA = SCHEMAS / "review-response.json"


def _frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML-frontmatter parser: key: value lines between the first two --- fences."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_exists_with_frontmatter() -> None:
    assert SKILL_MD.exists(), f"missing {SKILL_MD}"
    fm = _frontmatter(_skill_text())
    assert fm.get("name"), "SKILL.md frontmatter missing non-empty 'name'"
    assert fm.get("description"), "SKILL.md frontmatter missing non-empty 'description'"


def _section_body(text: str, header: str) -> str:
    """Return the text from a `#+ header` line up to the next header of the same-or-higher level."""
    m = re.search(rf"^(#+)\s*{re.escape(header)}\s*$", text, re.MULTILINE)
    assert m, f"missing section header: {header}"
    level = len(m.group(1))
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def test_skill_md_has_required_sections() -> None:
    text = _skill_text()
    for header in ("Review scopes", "Install", "Configure", "Sandbox configuration"):
        assert re.search(rf"^#+\s*{re.escape(header)}", text, re.MULTILINE), f"missing section: {header}"
    # Review scopes section names all three values — anchored to the actual section body
    scopes_section = _section_body(text, "Review scopes")
    for scope in ("lite", "standard", "full"):
        assert scope in scopes_section, f"Review scopes section does not mention '{scope}'"


def test_skill_md_sandbox_snippet_is_valid_json() -> None:
    text = _skill_text()
    section = _section_body(text, "Sandbox configuration")
    m = re.search(r"```json\n(.*?)\n```", section, re.DOTALL)
    assert m, "no ```json fenced block under Sandbox configuration"
    parsed = json.loads(m.group(1))
    assert "sandbox" in parsed, "sandbox snippet missing top-level 'sandbox' key"


def test_skill_md_has_status_section() -> None:
    section = _section_body(_skill_text(), "Status")
    assert "--capabilities" in section, "Status section must describe --capabilities state"
    assert "setup.sh" in section, "Status section must note setup.sh as forthcoming"


def test_skill_md_references_schemas() -> None:
    text = _skill_text()
    for ref in ("capabilities.json", "schemas/review-request.json", "schemas/review-response.json"):
        assert ref in text, f"SKILL.md does not reference {ref}"


@pytest.mark.parametrize("schema_path", [CAPABILITIES_SCHEMA, REQUEST_SCHEMA, RESPONSE_SCHEMA])
def test_contract_schemas_are_valid_jsonschema(schema_path: Path) -> None:
    assert schema_path.exists(), f"missing {schema_path}"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_review_response_schema_matches_s0_output() -> None:
    schema = json.loads(RESPONSE_SCHEMA.read_text(encoding="utf-8"))
    sample = {
        "analyzers": {
            "semgrep": {
                "sarif": {"version": "2.1.0", "runs": []},
                "metrics": None,
                "duration_s": 0.0,
                "status": "ok",
                "error": None,
            },
            "radon": {
                "sarif": {"version": "2.1.0", "runs": []},
                "metrics": {"per_file": {}, "per_class": {}, "coupling": {}},
                "duration_s": 0.0,
                "status": "ok",
                "error": None,
            },
        }
    }
    jsonschema.validate(sample, schema)
