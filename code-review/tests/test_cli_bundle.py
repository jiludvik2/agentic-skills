"""s1-t3 — the CLI emits a review-bundle.v1.json-valid ReviewBundle (ADR-0020 capstone).

After the strangle, `polyreview run` collects one raw CaptureOutput per analyzer and emits
the bundle directly — no SARIF aggregation, no findings parsing. These tests pin the new
contract: the emitted JSON validates against the published bundle schema, carries one
`outputs` entry per analyzer with its verbatim `command`, and the process exit code keys off
the ADR-0019 statuses (error/timeout → non-zero; all ok/unavailable → zero).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import jsonschema
import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.capture import CaptureOutput
from code_review.cli import app
from code_review.config import ConfigError
from code_review.contracts import ReviewRequest
from code_review.review_bundle import load_bundle_schema

runner = CliRunner()


class _OkCapture:
    name: ClassVar[str] = "ok_tool"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        return CaptureOutput(
            tool="ok_tool", stdout='{"raw": "tool output"}', exit_code=0,
            command=("ok_tool", "--run"),
        )


class _OkCapture2(_OkCapture):
    name: ClassVar[str] = "ok_tool2"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        return CaptureOutput(
            tool="ok_tool2", stdout="plain text", exit_code=0, command=("ok_tool2",)
        )


class _ErrCapture:
    name: ClassVar[str] = "err_tool"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        return CaptureOutput(
            tool="err_tool", status="error", exit_code=2, stderr="kaboom",
            error="exited 2: kaboom", command=("err_tool",),
        )


def test_run_emits_valid_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "ok_tool", _OkCapture)
    monkeypatch.setitem(adapters_mod.REGISTRY, "ok_tool2", _OkCapture2)

    result = runner.invoke(
        app, ["run", "--analyzer", "ok_tool", "--analyzer", "ok_tool2", "--target", "."]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    # Validates against the published bundle schema.
    jsonschema.validate(data, load_bundle_schema())
    assert data["schema"] == "polyreview/review-bundle/v1"
    # One outputs entry per selected analyzer, each carrying its verbatim argv.
    tools = {o["tool"] for o in data["outputs"]}
    assert tools == {"ok_tool", "ok_tool2"}
    assert all(o["command"] for o in data["outputs"]), "each output must echo a non-empty command"
    # Raw stdout reaches the agent verbatim — no parsing.
    by_tool = {o["tool"]: o for o in data["outputs"]}
    assert by_tool["ok_tool"]["stdout"] == '{"raw": "tool output"}'


def test_run_exit_code_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "ok_tool", _OkCapture)
    monkeypatch.setitem(adapters_mod.REGISTRY, "err_tool", _ErrCapture)

    # An all-ok run exits zero.
    ok = runner.invoke(app, ["run", "--analyzer", "ok_tool", "--target", "."])
    assert ok.exit_code == 0, ok.output

    # Any error capture flips the exit code; stdout is still parseable (no traceback leak).
    err = runner.invoke(
        app, ["run", "--analyzer", "ok_tool", "--analyzer", "err_tool", "--target", "."]
    )
    assert err.exit_code != 0
    data = json.loads(err.output)
    by_tool = {o["tool"]: o for o in data["outputs"]}
    assert by_tool["err_tool"]["status"] == "error"
    assert by_tool["err_tool"]["error"]


def test_adapter_exception_becomes_error_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    """A crashing adapter must not take down the CLI — it becomes an error capture in the
    bundle (the bundle still validates) and flips the exit code."""

    class _Boom:
        name: ClassVar[str] = "boom"
        kind: ClassVar[str] = "deterministic"
        default_timeout_s: ClassVar[int] = 30
        scope_restrictions: ClassVar[frozenset[str]] = frozenset()

        async def run(self, request: ReviewRequest) -> CaptureOutput:
            raise RuntimeError("adapter blew up")

    monkeypatch.setitem(adapters_mod.REGISTRY, "boom", _Boom)
    result = runner.invoke(app, ["run", "--analyzer", "boom", "--target", "."])
    assert result.exit_code != 0
    data = json.loads(result.output)
    jsonschema.validate(data, load_bundle_schema())
    boom = next(o for o in data["outputs"] if o["tool"] == "boom")
    assert boom["status"] == "error"
    assert "adapter blew up" in (boom["error"] or "")


class _TimeoutCapture:
    name: ClassVar[str] = "slow_tool"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        return CaptureOutput(
            tool="slow_tool", status="timeout", error="timed out after 30s",
            command=("slow_tool",),
        )


def test_run_exit_code_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A `timeout` capture flips the exit code too (a timed-out tool analysed nothing) —
    the documented other half of the non-zero rule, distinct from `error`."""
    monkeypatch.setitem(adapters_mod.REGISTRY, "slow_tool", _TimeoutCapture)
    result = runner.invoke(app, ["run", "--analyzer", "slow_tool", "--target", "."])
    assert result.exit_code != 0
    out = next(o for o in json.loads(result.output)["outputs"] if o["tool"] == "slow_tool")
    assert out["status"] == "timeout"


def test_output_summary_reports_per_status_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With --output, the summary replaces the old findings count with per-status counts —
    a mixed ok/error run must surface both."""
    monkeypatch.setitem(adapters_mod.REGISTRY, "ok_tool", _OkCapture)
    monkeypatch.setitem(adapters_mod.REGISTRY, "err_tool", _ErrCapture)
    monkeypatch.chdir(tmp_path)
    out_path = tmp_path / "bundle.json"
    result = runner.invoke(
        app,
        ["run", "--analyzer", "ok_tool", "--analyzer", "err_tool",
         "--output", str(out_path), "--target", "."],
    )
    assert result.exit_code != 0  # err present
    summary = result.output.strip()
    assert "ok: 1" in summary and "error: 1" in summary, repr(summary)
    assert "{" not in result.output  # JSON went to the file, not stdout


def test_config_error_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad config surfaces as a clean non-zero exit, not a traceback."""
    def _raise(_path: object) -> None:
        raise ConfigError("injected: bad toml")

    monkeypatch.setitem(adapters_mod.REGISTRY, "ok_tool", _OkCapture)
    monkeypatch.setattr("code_review.cli.load_config", _raise)
    result = runner.invoke(app, ["run", "--analyzer", "ok_tool", "--target", "."])
    assert result.exit_code != 0
    assert "injected: bad toml" in result.output
    assert "Traceback" not in result.output
