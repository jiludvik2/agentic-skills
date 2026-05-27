from __future__ import annotations

import json
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).parent.parent
CAPS = REPO_ROOT / "code_review" / "capabilities.json"
SCHEMA = REPO_ROOT / "code_review" / "schemas" / "capabilities.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _load_caps() -> dict:
    return json.loads(CAPS.read_text(encoding="utf-8"))


def test_capabilities_validates_against_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(_load_caps(), schema)


def test_capabilities_has_required_sections() -> None:
    caps = _load_caps()
    for key in ("review_kinds", "stack_coverage", "analyzers", "taxonomies"):
        assert key in caps, f"missing top-level section: {key}"


def test_review_kinds_minimum_set() -> None:
    caps = _load_caps()
    ids = {rk["id"] for rk in caps["review_kinds"]}
    assert {"per-task", "story-level", "contract-verification"} <= ids
    for rk in caps["review_kinds"]:
        assert rk["scope"] in ("diff", "cumulative-diff", "story-level-only")
        assert "min" in rk["expected_duration_s"] and "max" in rk["expected_duration_s"]


def test_analyzers_match_s0_registry() -> None:
    from code_review.adapters import REGISTRY

    caps = _load_caps()
    ana_ids = {a["id"] for a in caps["analyzers"]}
    assert {"semgrep", "radon"} <= ana_ids
    for a in caps["analyzers"]:
        assert a["id"] in REGISTRY, f"analyzer '{a['id']}' not in REGISTRY"
        required = ("kind", "languages", "rule_classes", "taxonomies_tagged", "default_timeout_s")
        for field in required:
            assert field in a, f"analyzer '{a['id']}' missing field '{field}'"


def test_taxonomies_include_sdlc_severity() -> None:
    caps = _load_caps()
    values = caps["taxonomies"]["sdlc-severity"]["values"]
    assert set(values) == {"critical", "important", "minor", "nit"}


def test_stack_coverage_frameworks_have_fixtures() -> None:
    """Coverage discipline: anything marked verified must be backed by a real fixture."""
    caps = _load_caps()
    fixture_dirs = [p.name for p in FIXTURES.iterdir() if p.is_dir()]
    for lang, info in caps["stack_coverage"].items():
        if info.get("status") == "verified":
            assert any(lang in d for d in fixture_dirs), (
                f"verified language '{lang}' lacks a fixture"
            )
        for fw in info.get("frameworks", []):
            if fw.get("status") == "verified":
                assert any(fw["name"] in d for d in fixture_dirs), (
                    f"verified framework '{fw['name']}' lacks a fixture"
                )
