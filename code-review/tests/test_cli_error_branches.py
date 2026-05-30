"""Locking tests for the three untested cli.py error branches (FINDINGS.md F10,
story s5-cli-error-branch-coverage).

These branches are user-facing error contracts that must not regress silently:

1. unknown ``--analyzer <name>``           → cli.py "unknown analyzer(s): …"
2. explicitly selecting a disabled analyzer → cli.py "analyzer(s) disabled in
   code-review.toml: …"
3. empty selection after filtering          → cli.py "no analyzers selected
   after filtering"

Test-only: no production change is expected — the branches already exist; these
tests lock their contract. Pattern mirrors test_review_selection_validation.py
(``CliRunner(capture="fd")`` + REGISTRY patch with ``FakeAnalyzer``).
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.cli import app
from code_review.config import Config
from tests.conftest import FakeAnalyzer

ALL_ANALYZER_NAMES = [
    "semgrep", "bandit", "gitleaks", "trivy",
    "radon", "vulture", "knip", "jscpd", "eslint",
    "pydeps", "depcruiser", "cohesion", "schemathesis",
]


def _patch_all(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ALL_ANALYZER_NAMES:
        monkeypatch.setitem(adapters_mod.REGISTRY, name, FakeAnalyzer)


# ---------------------------------------------------------------------------
# Branch 1: unknown --analyzer rejected
# ---------------------------------------------------------------------------

def test_unknown_analyzer_exits_nonzero_with_message(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["--analyzer", "nonesuch", "--target", "."])
    assert result.exit_code != 0
    assert "unknown analyzer" in result.stderr.lower()
    assert "nonesuch" in result.stderr


# ---------------------------------------------------------------------------
# Branch 2: explicitly selected disabled analyzer rejected
# ---------------------------------------------------------------------------

def test_disabled_analyzer_selected_exits_nonzero_with_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_all(monkeypatch)
    # Config that disables the explicitly-selected analyzer; bypasses the
    # CWD code-review.toml lookup entirely.
    monkeypatch.setattr(
        "code_review.cli.load_config",
        lambda _path: Config(disabled_analyzers=["semgrep"]),
    )
    runner = CliRunner(capture="fd")
    result = runner.invoke(app, ["--analyzer", "semgrep", "--target", "."])
    assert result.exit_code != 0
    assert "disabled in code-review.toml" in result.stderr
    assert "semgrep" in result.stderr


# ---------------------------------------------------------------------------
# Branch 3: empty selection after filtering rejected
# ---------------------------------------------------------------------------

def test_empty_selection_exits_nonzero_with_message(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all(monkeypatch)
    runner = CliRunner(capture="fd")

    # Positive control: --review security is a non-empty selection without a
    # language filter. This pins the test's load-bearing precondition — every
    # security analyzer declares a (python/js/ts) language list, none match-all
    # — so if a future capabilities.json edit broke that, this control fails
    # loudly here rather than silently turning the empty-selection case below
    # into a success-path that no longer exercises the cli.py branch.
    control = runner.invoke(app, ["--review", "security", "--target", "."])
    assert control.exit_code == 0, control.output

    # Filtering that same selection by an unsupported language excludes every
    # analyzer → empty, but with no selector error, so control reaches the
    # cli.py "no analyzers selected after filtering" branch (not an earlier
    # selector error or parser rejection).
    result = runner.invoke(
        app, ["--review", "security", "--language", "go", "--target", "."]
    )
    assert result.exit_code != 0
    assert "no analyzers selected" in result.stderr.lower()
