"""CLI-level tests for Validation, warnings, and normalization scenarios
(s5-review-selection-scheme.md §Validation, warnings, and normalization).

Uses CliRunner(mix_stderr=False) to assert warnings go to stderr and the
JSON/stdout summary is unaffected.  Assertions always check both channel
and exit code.
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
# Case-insensitive --review and --depth
# ---------------------------------------------------------------------------

def test_uppercase_review_and_depth_accepted_no_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--review", "SECURITY", "--depth", "FULL", "--target", "."])
    assert result.exit_code == 0, result.output
    assert not result.stderr
    ran = _ran(result.stdout)
    assert {"semgrep", "bandit", "gitleaks", "trivy"} <= ran


def test_mixed_case_review_matches_lowercase(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    lower = runner.invoke(app, ["run", "--review", "security", "--depth", "quick", "--target", "."])
    upper = runner.invoke(app, ["run", "--review", "Security", "--depth", "Quick", "--target", "."])
    assert lower.exit_code == 0 and upper.exit_code == 0
    assert _ran(lower.stdout) == _ran(upper.stdout)


# ---------------------------------------------------------------------------
# Subcategory + explicit --depth → depth ignored with warning to stderr
# ---------------------------------------------------------------------------

def test_subcategory_plus_explicit_depth_emits_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--review", "secrets", "--depth", "full", "--target", "."])
    assert result.exit_code == 0
    assert "ignored" in result.stderr.lower() or "depth" in result.stderr.lower()
    assert _ran(result.stdout) == {"gitleaks"}
    # stdout JSON must not contain the warning text
    assert "ignored" not in result.stdout


def test_coupling_plus_depth_quick_emits_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app, ["run", "--review", "coupling", "--depth", "quick", "--target", "."]
    )
    assert result.exit_code == 0
    assert "depth" in result.stderr.lower()
    assert _ran(result.stdout) == {"pydeps", "depcruiser"}


# ---------------------------------------------------------------------------
# Contradictory --depth → simpler (quick) wins with warning to stderr
# ---------------------------------------------------------------------------

def test_contradictory_depth_quick_wins_with_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--depth", "quick", "--depth", "full", "--target", "."])
    assert result.exit_code == 0
    assert "quick" in result.stderr
    ran = _ran(result.stdout)
    # quick tier only — trivy (full) should NOT be present
    assert "trivy" not in ran
    assert "semgrep" in ran


def test_contradictory_depth_warning_not_in_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--depth", "quick", "--depth", "full", "--target", "."])
    assert result.exit_code == 0
    # Warning keywords must be on stderr only
    assert "conflicting" not in result.stdout and "simpler" not in result.stdout


# ---------------------------------------------------------------------------
# Unknown --depth value rejected by the parser
# ---------------------------------------------------------------------------

def test_unknown_depth_value_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--depth", "bogus", "--target", "."])
    assert result.exit_code != 0


def test_unknown_depth_error_mentions_valid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--depth", "bogus", "--target", "."])
    combined = result.output + result.stderr
    assert "quick" in combined and "full" in combined


# ---------------------------------------------------------------------------
# Unknown --review value errors with valid options
# ---------------------------------------------------------------------------

def test_unknown_review_value_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--review", "bogus", "--target", "."])
    assert result.exit_code != 0


def test_unknown_review_value_error_lists_valid_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--review", "bogus", "--target", "."])
    combined = result.output + result.stderr
    for domain in ("security", "maintainability"):
        assert domain in combined, f"valid domain {domain!r} not mentioned in error output"


# ---------------------------------------------------------------------------
# --review-scope is gone
# ---------------------------------------------------------------------------

def test_review_scope_flag_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--review-scope", "standard", "--target", "."])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Default: no selection flags → quick whole review
# ---------------------------------------------------------------------------

def test_default_no_flags_runs_quick_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["run", "--target", "."])
    assert result.exit_code == 0, result.output
    assert _ran(result.stdout) == {
        "semgrep", "bandit", "gitleaks", "radon", "vulture", "knip", "jscpd", "eslint"
    }


# ---------------------------------------------------------------------------
# --analyzer overrides --review / --depth
# ---------------------------------------------------------------------------

def test_analyzer_override_ignores_review_and_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app,
        ["run", "--analyzer", "semgrep", "--review", "maintainability",
         "--depth", "full", "--target", "."],
    )
    assert result.exit_code == 0
    assert _ran(result.stdout) == {"semgrep"}


# ---------------------------------------------------------------------------
# contracts/conformance removed (ADR-0021) → now unknown-value errors
# ---------------------------------------------------------------------------

def test_conformance_now_unknown_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app, ["run", "--review", "conformance", "--scope", "story-level", "--target", "."]
    )
    assert result.exit_code != 0
    combined = result.output + result.stderr
    assert "conformance" in combined


def test_contracts_now_unknown_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app, ["run", "--review", "contracts", "--target", "."]
    )
    assert result.exit_code != 0
    combined = result.output + result.stderr
    assert "contracts" in combined
