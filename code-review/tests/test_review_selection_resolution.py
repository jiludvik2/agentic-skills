"""Unit tests for selector.resolve_review_selection().

Table-driven over the resolution precedence rules in s5-review-selection-scheme.md.
Tests call the selector directly (no CLI, no I/O) for speed and isolation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from code_review.selector import resolve_review_selection

CAPS_PATH = Path(__file__).parent.parent / "code_review" / "capabilities.json"


@pytest.fixture
def taxonomy() -> list[dict[str, Any]]:
    analyzers: list[dict[str, Any]] = json.loads(CAPS_PATH.read_text())["analyzers"]
    return analyzers


# ---------------------------------------------------------------------------
# Rule 2: --review <domain> + --depth
# ---------------------------------------------------------------------------

def test_security_quick_selects_vulnerabilities_and_secrets(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["security"], depth="quick", scope="per-task"
    )
    assert set(result.analyzers) == {"semgrep", "bandit", "gitleaks"}
    assert not result.warnings
    assert result.error is None


def test_security_full_adds_trivy(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["security"], depth="full", scope="per-task"
    )
    assert set(result.analyzers) == {"semgrep", "bandit", "gitleaks", "trivy"}
    assert not result.warnings


def test_maintainability_quick_selects_correct_analyzers(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["maintainability"], depth="quick", scope="per-task"
    )
    assert set(result.analyzers) == {"radon", "vulture", "knip", "jscpd", "eslint"}


def test_maintainability_full_adds_coupling_and_cohesion(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["maintainability"], depth="full", scope="per-task"
    )
    expected = {"radon", "vulture", "knip", "jscpd", "eslint", "pydeps", "depcruiser", "cohesion"}
    assert set(result.analyzers) == expected


# ---------------------------------------------------------------------------
# Rule 3: --review <subcategory> (depth-independent)
# ---------------------------------------------------------------------------

def test_subcategory_secrets_selects_gitleaks_ignores_depth(taxonomy: list[dict[str, Any]]) -> None:
    for depth in ("quick", "full"):
        result = resolve_review_selection(
            taxonomy, review=["secrets"], depth=depth, scope="per-task"
        )
        assert set(result.analyzers) == {"gitleaks"}, f"failed at depth={depth!r}"


def test_subcategory_coupling_selects_both_tools_even_at_quick_depth(
    taxonomy: list[dict[str, Any]],
) -> None:
    result = resolve_review_selection(
        taxonomy, review=["coupling"], depth="quick", scope="per-task"
    )
    assert set(result.analyzers) == {"pydeps", "depcruiser"}


# ---------------------------------------------------------------------------
# Rule 4: --depth alone (standalone depth across all domains)
# ---------------------------------------------------------------------------

def test_standalone_depth_quick_selects_all_quick_analyzers(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(taxonomy, review=[], depth="quick", scope="per-task")
    expected = {"semgrep", "bandit", "gitleaks", "radon", "vulture", "knip", "jscpd", "eslint"}
    assert set(result.analyzers) == expected


def test_standalone_depth_full_at_per_task_excludes_story_level(
    taxonomy: list[dict[str, Any]],
) -> None:
    result = resolve_review_selection(taxonomy, review=[], depth="full", scope="per-task")
    expected = {
        "semgrep", "bandit", "gitleaks", "trivy",
        "radon", "vulture", "knip", "jscpd", "eslint",
        "pydeps", "depcruiser", "cohesion",
    }
    assert set(result.analyzers) == expected


# ---------------------------------------------------------------------------
# Rule 5: default (no flags) behaves identically to --depth quick
# ---------------------------------------------------------------------------

def test_no_review_no_depth_equals_depth_quick(taxonomy: list[dict[str, Any]]) -> None:
    default_result = resolve_review_selection(taxonomy, review=[], depth="quick", scope="per-task")
    quick_result = resolve_review_selection(taxonomy, review=[], depth="quick", scope="per-task")
    assert default_result.analyzers == quick_result.analyzers


# ---------------------------------------------------------------------------
# Rule 6: multiple --review values are unioned
# ---------------------------------------------------------------------------

def test_union_complexity_and_coupling(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["complexity", "coupling"], depth="quick", scope="per-task"
    )
    assert set(result.analyzers) == {"radon", "pydeps", "depcruiser"}
    assert not result.warnings


def test_union_security_and_maintainability_quick(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["security", "maintainability"], depth="quick", scope="per-task"
    )
    expected = {"semgrep", "bandit", "gitleaks", "radon", "vulture", "knip", "jscpd", "eslint"}
    assert set(result.analyzers) == expected
    assert not result.warnings


# ---------------------------------------------------------------------------
# Rule 7: language filter
# ---------------------------------------------------------------------------

def test_python_diff_trims_js_only_analyzers(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy,
        review=["maintainability"],
        depth="quick",
        scope="per-task",
        diff_languages=frozenset({"python"}),
    )
    # knip, jscpd, eslint are js/ts only → excluded
    assert set(result.analyzers) == {"radon", "vulture"}


def test_python_diff_security_quick_all_eligible(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy,
        review=["security"],
        depth="quick",
        scope="per-task",
        diff_languages=frozenset({"python"}),
    )
    # semgrep: py,js,ts ✓  bandit: py ✓  gitleaks: py,js,ts ✓
    assert set(result.analyzers) == {"semgrep", "bandit", "gitleaks"}


def test_js_diff_excludes_python_only_analyzers(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy,
        review=["security"],
        depth="quick",
        scope="per-task",
        diff_languages=frozenset({"javascript"}),
    )
    # bandit: python only → excluded
    assert "bandit" not in result.analyzers
    assert "semgrep" in result.analyzers
    assert "gitleaks" in result.analyzers


# ---------------------------------------------------------------------------
# Contracts removed (ADR-0021): the domain and its `conformance` subcategory no
# longer exist, so both resolve as unknown values.
# ---------------------------------------------------------------------------

def test_contracts_domain_now_unknown(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["contracts"], depth="full", scope="story-level"
    )
    assert result.analyzers == []
    assert result.error is not None
    assert "Unknown" in result.error and "contracts" in result.error


def test_conformance_subcategory_now_unknown(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["conformance"], depth="full", scope="story-level"
    )
    assert result.analyzers == []
    assert result.error is not None
    assert "Unknown" in result.error and "conformance" in result.error


# ---------------------------------------------------------------------------
# Unknown value error
# ---------------------------------------------------------------------------

def test_unknown_review_value_returns_error(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(taxonomy, review=["bogus"], depth="quick", scope="per-task")
    assert result.analyzers == []
    assert result.error is not None
    assert "bogus" in result.error
    assert "security" in result.error  # lists valid options


# ---------------------------------------------------------------------------
# Redundancy warning (Rule 6)
# ---------------------------------------------------------------------------

def test_domain_plus_same_domain_subcategory_emits_redundancy_warning(
    taxonomy: list[dict[str, Any]],
) -> None:
    # secrets is in security@quick → redundant when security is also requested
    result = resolve_review_selection(
        taxonomy, review=["security", "secrets"], depth="quick", scope="per-task"
    )
    assert set(result.analyzers) == {"semgrep", "bandit", "gitleaks"}
    assert any("redundant" in w for w in result.warnings)
    assert any("secrets" in w for w in result.warnings)


def test_domain_plus_different_domain_subcategory_is_additive(
    taxonomy: list[dict[str, Any]],
) -> None:
    result = resolve_review_selection(
        taxonomy, review=["security", "coupling"], depth="quick", scope="per-task"
    )
    assert set(result.analyzers) == {"semgrep", "bandit", "gitleaks", "pydeps", "depcruiser"}
    assert not result.warnings


def test_domain_plus_tier_extending_subcategory_is_additive(taxonomy: list[dict[str, Any]]) -> None:
    # dependencies (trivy) is security@full; security@quick alone wouldn't include it
    result = resolve_review_selection(
        taxonomy, review=["security", "dependencies"], depth="quick", scope="per-task"
    )
    assert set(result.analyzers) == {"semgrep", "bandit", "gitleaks", "trivy"}
    assert not result.warnings


# ---------------------------------------------------------------------------
# depth_explicit flag: depth-ignored warning when all review values are subcategories
# ---------------------------------------------------------------------------

def test_subcategory_only_with_explicit_depth_emits_ignored_warning(
    taxonomy: list[dict[str, Any]],
) -> None:
    result = resolve_review_selection(
        taxonomy, review=["secrets"], depth="full", scope="per-task", depth_explicit=True
    )
    assert set(result.analyzers) == {"gitleaks"}
    assert any("ignored" in w.lower() for w in result.warnings)
    assert any("depth" in w.lower() for w in result.warnings)


def test_subcategory_only_without_explicit_depth_no_warning(taxonomy: list[dict[str, Any]]) -> None:
    result = resolve_review_selection(
        taxonomy, review=["secrets"], depth="full", scope="per-task", depth_explicit=False
    )
    assert set(result.analyzers) == {"gitleaks"}
    # No warning — depth was implicit (the default)
    assert not any("ignored" in w.lower() for w in result.warnings)


def test_domain_plus_subcategory_explicit_depth_no_ignored_warning(
    taxonomy: list[dict[str, Any]],
) -> None:
    # When at least one domain is present, depth is NOT ignored (used for domain expansion)
    result = resolve_review_selection(
        taxonomy,
        review=["security", "coupling"],
        depth="quick",
        scope="per-task",
        depth_explicit=True,
    )
    assert not any("ignored" in w.lower() for w in result.warnings)
