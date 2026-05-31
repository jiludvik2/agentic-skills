"""CLI-level tests for Combinations scenarios (s5-review-selection-scheme.md §Combinations).

Uses CliRunner(mix_stderr=False) so warnings on stderr are asserted separately from
the JSON output on stdout.  All real adapters are replaced with FakeAnalyzers so no
external tools are invoked; which analyzers RAN is read from the JSON output's
top-level "analyzers" key.
"""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.cli import app
from tests.conftest import FakeAnalyzer

ALL_ANALYZER_NAMES = [
    "semgrep", "bandit", "gitleaks", "trivy",
    "radon", "vulture", "knip", "jscpd", "eslint",
    "pydeps", "depcruiser", "cohesion",
]


def _patch_all(monkeypatch: pytest.MonkeyPatch) -> None:
    # Each fake must report its own name: the bundle keys outputs by the adapter's
    # self-reported `tool`, so a single shared FakeAnalyzer (name="fake") would collapse
    # every selected analyzer to one output. Give each a uniquely-named subclass.
    for name in ALL_ANALYZER_NAMES:
        cls = type(name, (FakeAnalyzer,), {"name": name})
        monkeypatch.setitem(adapters_mod.REGISTRY, name, cls)


def _ran(stdout: str) -> set[str]:
    return {o["tool"] for o in json.loads(stdout)["outputs"]}


# ---------------------------------------------------------------------------
# Multiple domains are unioned — no warning
# ---------------------------------------------------------------------------

def test_multiple_domains_unioned_no_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app,
        ["run", "--review", "security", "--review", "maintainability",
         "--depth", "quick", "--target", "."],
    )
    assert result.exit_code == 0, result.output
    expected = {"semgrep", "bandit", "gitleaks", "radon", "vulture", "knip", "jscpd", "eslint"}
    assert _ran(result.stdout) == expected
    assert not result.stderr


# ---------------------------------------------------------------------------
# Domain + same-domain subcategory → redundancy warning to stderr
# ---------------------------------------------------------------------------

def test_domain_same_subcategory_redundancy_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app, ["run", "--review", "security", "--review", "secrets", "--target", "."]
    )
    assert result.exit_code == 0
    assert _ran(result.stdout) == {"semgrep", "bandit", "gitleaks"}
    assert "redundant" in result.stderr
    assert "secrets" in result.stderr
    # Warning must NOT appear in stdout JSON
    assert "redundant" not in result.stdout


# ---------------------------------------------------------------------------
# Domain + different-domain subcategory → additive, no warning
# ---------------------------------------------------------------------------

def test_domain_different_subcategory_additive_no_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app,
        ["run", "--review", "security", "--review", "coupling",
         "--depth", "quick", "--target", "."],
    )
    assert result.exit_code == 0
    assert _ran(result.stdout) == {"semgrep", "bandit", "gitleaks", "pydeps", "depcruiser"}
    assert not result.stderr


# ---------------------------------------------------------------------------
# Domain + tier-extending subcategory → additive (adds tools not in domain@depth)
# ---------------------------------------------------------------------------

def test_domain_tier_extending_subcategory_additive(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app,
        ["run", "--review", "security", "--review", "dependencies",
         "--depth", "quick", "--target", "."],
    )
    assert result.exit_code == 0
    ran = _ran(result.stdout)
    assert ran == {"semgrep", "bandit", "gitleaks", "trivy"}
    assert not result.stderr


# ---------------------------------------------------------------------------
# Duplicate --review value → deduplicated + warning to stderr
# ---------------------------------------------------------------------------

def test_duplicate_review_value_deduped_warning_to_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app, ["run", "--review", "security", "--review", "security", "--target", "."]
    )
    assert result.exit_code == 0
    assert _ran(result.stdout) == {"semgrep", "bandit", "gitleaks"}
    assert "security" in result.stderr
    # Warning message keywords
    assert any(kw in result.stderr.lower() for kw in ("duplicate", "multiple", "ignored"))
    # Warning must NOT appear in stdout JSON
    assert "duplicate" not in result.stdout and "multiple" not in result.stdout
