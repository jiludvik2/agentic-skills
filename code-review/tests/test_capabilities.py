from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).parent.parent
CAPS = REPO_ROOT / "code_review" / "capabilities.json"
SCHEMA = REPO_ROOT / "code_review" / "schemas" / "capabilities.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _load_caps() -> dict[str, Any]:
    caps: dict[str, Any] = json.loads(CAPS.read_text(encoding="utf-8"))
    return caps


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
    assert {"per-task", "story-level"} <= ids
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


def test_no_contract_analyzer_remains() -> None:
    """ADR-0021: Schemathesis and the contracts domain were removed from code-review."""
    caps = _load_caps()
    ids = {a["id"] for a in caps["analyzers"]}
    assert "schemathesis" not in ids
    assert all(a["domain"] != "contracts" for a in caps["analyzers"])
    assert all(rk["id"] != "contract-verification" for rk in caps["review_kinds"])


def test_all_analyzers_have_taxonomy_tags() -> None:
    caps = _load_caps()
    valid_domains = {"security", "maintainability"}
    valid_tiers = {"quick", "full"}
    for a in caps["analyzers"]:
        aid = a["id"]
        assert "domain" in a, f"{aid}: missing 'domain'"
        assert "subcategory" in a, f"{aid}: missing 'subcategory'"
        assert "tier" in a, f"{aid}: missing 'tier'"
        assert a["domain"] in valid_domains, f"{aid}: domain '{a['domain']}' not in {valid_domains}"
        assert a["tier"] in valid_tiers, f"{aid}: tier '{a['tier']}' not in {valid_tiers}"
        assert isinstance(a["subcategory"], str) and a["subcategory"], (
            f"{aid}: subcategory must be non-empty string"
        )


def test_taxonomy_matches_locked_table() -> None:
    """Every row in the s5 locked taxonomy table is reflected in capabilities.json."""
    caps = _load_caps()
    entries = {a["id"]: a for a in caps["analyzers"]}
    expected = [
        ("semgrep", "security", "vulnerabilities", "quick"),
        ("bandit", "security", "vulnerabilities", "quick"),
        ("gitleaks", "security", "secrets", "quick"),
        ("trivy", "security", "dependencies", "full"),
        ("radon", "maintainability", "complexity", "quick"),
        ("jscomplexity", "maintainability", "complexity", "quick"),
        ("vulture", "maintainability", "dead-code", "quick"),
        ("knip", "maintainability", "dead-code", "quick"),
        ("jscpd", "maintainability", "duplication", "quick"),
        ("eslint", "maintainability", "quality", "quick"),
        ("pydeps", "maintainability", "coupling", "full"),
        ("depcruiser", "maintainability", "coupling", "full"),
        ("cohesion", "maintainability", "cohesion", "full"),
    ]
    for aid, domain, subcategory, tier in expected:
        assert aid in entries, f"{aid} missing from capabilities.json"
        a = entries[aid]
        assert a["domain"] == domain, f"{aid}: expected domain={domain!r}, got {a['domain']!r}"
        assert a["subcategory"] == subcategory, (
            f"{aid}: expected subcategory={subcategory!r}, got {a['subcategory']!r}"
        )
        assert a["tier"] == tier, f"{aid}: expected tier={tier!r}, got {a['tier']!r}"


def test_jscomplexity_advertises_typescript() -> None:
    """story-jscomplexity-ts: once @typescript-eslint/parser is vendored, jscomplexity
    covers TypeScript too — so a TS diff routes to it (was JS-only per ADR-0022 s4-t1)."""
    caps = _load_caps()
    jsc = next(a for a in caps["analyzers"] if a["id"] == "jscomplexity")
    assert "typescript" in jsc["languages"], (
        f"jscomplexity must advertise typescript; got {jsc['languages']}"
    )
    assert "javascript" in jsc["languages"], "JS coverage must remain"


def test_capabilities_node_versions_match_lockfile() -> None:
    """Drift guard: advertised Node-tool versions must equal the locked versions.

    Each vendored Node analyzer carries ``npm_package`` + ``version`` in
    capabilities.json; ``package-lock.json`` is the source of truth for what
    ``setup.sh`` installs (ADR-0017). If the lockfile is bumped without updating
    capabilities (or vice versa) this fails, surfacing the drift the
    ``--capabilities`` output would otherwise hide.
    """
    lockfile = REPO_ROOT / ".claude" / "skills" / "code-review" / "package-lock.json"
    locked = json.loads(lockfile.read_text(encoding="utf-8"))["packages"]
    caps = _load_caps()
    node_analyzers = [a for a in caps["analyzers"] if "npm_package" in a]
    advertised = {a["id"] for a in node_analyzers}
    assert {"eslint", "knip", "jscpd", "depcruiser"} <= advertised, (
        "all four vendored Node analyzers must advertise npm_package for the drift guard"
    )
    for a in node_analyzers:
        assert "version" in a, f"{a['id']}: advertises npm_package but no version"
        key = f"node_modules/{a['npm_package']}"
        assert key in locked, f"{a['npm_package']} not found in package-lock.json"
        assert a["version"] == locked[key]["version"], (
            f"{a['id']}: capabilities advertises {a['version']!r} but lockfile has "
            f"{locked[key]['version']!r} for {a['npm_package']}"
        )
    # The eslint SARIF formatter is vendored + version-pinned too (ADR-0017) and
    # is hard-required by the eslint adapter, but has no analyzer row of its own;
    # guard it against drift via the eslint entry's sarif_formatter.
    eslint = next(a for a in caps["analyzers"] if a["id"] == "eslint")
    fmt = eslint["sarif_formatter"]
    fkey = f"node_modules/{fmt['npm_package']}"
    assert fkey in locked, f"{fmt['npm_package']} not found in package-lock.json"
    assert fmt["version"] == locked[fkey]["version"], (
        f"eslint sarif_formatter advertises {fmt['version']!r} but lockfile has "
        f"{locked[fkey]['version']!r} for {fmt['npm_package']}"
    )


def test_eslint_is_quality_only_not_security() -> None:
    caps = _load_caps()
    eslint = next(a for a in caps["analyzers"] if a["id"] == "eslint")
    assert "security" not in eslint["rule_classes"], (
        "eslint must not be in security rule_class; JS/TS vulnerability coverage is via semgrep"
    )
    assert "quality" in eslint["rule_classes"]


def test_capabilities_schema_enforces_taxonomy_enums() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    caps = _load_caps()
    # Bad domain should fail validation
    bad = dict(caps)
    bad["analyzers"] = [dict(a) for a in caps["analyzers"]]
    bad["analyzers"][0] = {**bad["analyzers"][0], "domain": "invalid-domain"}
    try:
        jsonschema.validate(bad, schema)
        raise AssertionError("expected ValidationError for invalid domain")
    except jsonschema.ValidationError:
        pass
    # Bad tier should fail validation
    bad2 = dict(caps)
    bad2["analyzers"] = [dict(a) for a in caps["analyzers"]]
    bad2["analyzers"][0] = {**bad2["analyzers"][0], "tier": "medium"}
    try:
        jsonschema.validate(bad2, schema)
        raise AssertionError("expected ValidationError for invalid tier")
    except jsonschema.ValidationError:
        pass


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
