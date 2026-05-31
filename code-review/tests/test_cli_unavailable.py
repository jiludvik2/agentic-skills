"""End-to-end coverage that an `unavailable` analyzer status threads benignly
through the CLI exit contract (s0-fix2, story-level Review of s0).

The CLI computes ``has_error = any(v["status"] == "error" ...)`` (cli.py) and
exits 1 only when that is true. ADR-0019's `unavailable` (a clean "nothing to run
here" skip) must NOT trip that gate. These tests lock the contract end-to-end —
the per-task reviews verified it by code inspection only — so a future broadening
of the gate (e.g. ``status != "ok"``) is caught here rather than silently turning
clean skips into non-zero exits.

Test-only: no production change is expected. Pattern mirrors
test_cli_error_branches.py (``CliRunner(capture="fd")`` + REGISTRY patch).
"""
from __future__ import annotations

from typing import ClassVar

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.capture import CaptureOutput
from code_review.cli import app
from code_review.contracts import ReviewRequest


class _StatusAnalyzer:
    """A fake analyzer whose run() returns a fixed status — subclasses set it."""

    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    name: ClassVar[str] = "fake"
    _status: ClassVar[str] = "ok"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        return CaptureOutput(
            tool=self.name,
            status=self._status,
            error=None if self._status == "ok" else f"{self._status} reason",
            command=(self.name,),
        )


class _UnavailableAnalyzer(_StatusAnalyzer):
    name: ClassVar[str] = "bandit"
    _status: ClassVar[str] = "unavailable"


class _OkAnalyzer(_StatusAnalyzer):
    name: ClassVar[str] = "gitleaks"
    _status: ClassVar[str] = "ok"


class _ErrorAnalyzer(_StatusAnalyzer):
    name: ClassVar[str] = "semgrep"
    _status: ClassVar[str] = "error"


def test_all_ok_and_unavailable_run_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """A run whose analyzers are all ok / unavailable (none `error`) exits 0 —
    `unavailable` is benign for the CLI exit contract."""
    monkeypatch.setitem(adapters_mod.REGISTRY, "bandit", _UnavailableAnalyzer)
    monkeypatch.setitem(adapters_mod.REGISTRY, "gitleaks", _OkAnalyzer)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app, ["run", "--analyzer", "bandit", "--analyzer", "gitleaks", "--target", "."]
    )
    assert result.exit_code == 0, result.output


def test_any_error_status_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression guard: a real `error` status still flips the exit code, so the
    benign-`unavailable` test above is not just asserting a dead gate."""
    monkeypatch.setitem(adapters_mod.REGISTRY, "semgrep", _ErrorAnalyzer)
    monkeypatch.setitem(adapters_mod.REGISTRY, "gitleaks", _OkAnalyzer)
    runner = CliRunner(capture="fd")
    result = runner.invoke(
        app, ["run", "--analyzer", "semgrep", "--analyzer", "gitleaks", "--target", "."]
    )
    assert result.exit_code != 0, result.output
