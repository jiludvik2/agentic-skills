import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import ClassVar

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.capture import CaptureOutput
from code_review.cli import app
from code_review.contracts import ReviewRequest
from tests.conftest import FakeAnalyzer, FakeAnalyzer2, SlowFakeAnalyzer

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _tools(output: str) -> set[str]:
    """Tool names from a CLI-emitted review bundle."""
    return {o["tool"] for o in json.loads(output)["outputs"]}


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    # COLUMNS=200 guards against the secondary failure mode where a narrow
    # terminal (Rich defaults to 80 cols with no TTY) truncates option names
    # like "--analyzer" -> "analyz…". Note this alone is NOT enough: in a
    # color-enabled environment Rich styles each option's two leading dashes as
    # separate ANSI spans ("-\x1b[...]-analyzer"), so the literal "--analyzer"
    # is absent from the raw bytes regardless of width. Callers that assert on
    # help text must run it through _strip_ansi() first (see test_help_exits_zero).
    return subprocess.run(
        [sys.executable, "-m", "code_review.cli", "run", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "COLUMNS": "200"},
    )


def test_help_exits_zero() -> None:
    result = _run("--help")
    assert result.returncode == 0
    help_text = _strip_ansi(result.stdout)
    assert "--analyzer" in help_text
    assert "--output" in help_text


def test_capabilities_stub_exits_zero() -> None:
    result = _run("--capabilities")
    assert result.returncode == 0
    json.loads(result.stdout)


def test_output_tmp_rejected() -> None:
    result = _run("--output", "/tmp/x.json")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "sandbox" in combined.lower() or "cwd" in combined.lower()
    assert not Path("/tmp/x.json").exists()


def test_output_home_rejected() -> None:
    path = str(Path.home() / "review.json")
    result = _run("--output", path)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "sandbox" in combined.lower() or "cwd" in combined.lower()
    assert not Path(path).exists()


def test_output_etc_rejected() -> None:
    result = _run("--output", "/etc/review.json")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "sandbox" in combined.lower() or "cwd" in combined.lower()
    assert not Path("/etc/review.json").exists()


def test_concurrent_execution_faster_than_sequential(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Slow1(SlowFakeAnalyzer):
        name = "slow1"
        sleep_s = 0.2

    class _Slow2(SlowFakeAnalyzer):
        name = "slow2"
        sleep_s = 0.2

    monkeypatch.setitem(adapters_mod.REGISTRY, "slow1", _Slow1)
    monkeypatch.setitem(adapters_mod.REGISTRY, "slow2", _Slow2)

    runner = CliRunner()
    start = time.monotonic()
    result = runner.invoke(
        app, ["run", "--analyzer", "slow1", "--analyzer", "slow2", "--target", "."]
    )
    elapsed = time.monotonic() - start

    assert result.exit_code == 0, result.output
    assert elapsed < 0.35, f"Elapsed {elapsed:.3f}s suggests sequential execution"


def test_bundle_output_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake2", FakeAnalyzer2)

    runner = CliRunner()
    result = runner.invoke(
        app, ["run", "--analyzer", "fake", "--analyzer", "fake2", "--target", "."]
    )

    assert result.exit_code == 0, result.output
    assert _tools(result.output) == {"fake", "fake2"}


def test_diff_scope_excludes_unchanged_files(monkeypatch: pytest.MonkeyPatch) -> None:
    received_paths: list[tuple[str, ...]] = []

    class PathCapturingFake:
        name = "fake"
        kind = "deterministic"
        default_timeout_s = 30
        scope_restrictions: frozenset[str] = frozenset()

        async def run(self, request: object) -> CaptureOutput:
            assert isinstance(request, ReviewRequest)
            received_paths.append(request.target_paths)
            return CaptureOutput(tool="fake", command=("fake",))

    async def _mock_resolve(repo_root: object, diff_range: object) -> tuple[str, ...]:
        return ("changed.py",)

    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", PathCapturingFake)
    monkeypatch.setattr("code_review.cli.resolve_diff_paths", _mock_resolve)

    runner = CliRunner()
    result = runner.invoke(app, ["run", "--analyzer", "fake", "--diff", "HEAD~1..HEAD"])

    assert result.exit_code == 0, result.output
    assert received_paths == [("changed.py",)], f"Expected only changed.py; got {received_paths}"
    assert "unchanged.py" not in str(result.output)


def test_adapter_error_does_not_crash_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    class OkAdapter:
        name: ClassVar[str] = "ok_adapter"
        kind: ClassVar[str] = "deterministic"
        default_timeout_s: ClassVar[int] = 30
        scope_restrictions: ClassVar[frozenset[str]] = frozenset()

        async def run(self, request: ReviewRequest) -> CaptureOutput:
            return CaptureOutput(tool="ok_adapter", status="ok", command=("ok_adapter",))

    class ErrAdapter:
        name: ClassVar[str] = "err_adapter"
        kind: ClassVar[str] = "deterministic"
        default_timeout_s: ClassVar[int] = 30
        scope_restrictions: ClassVar[frozenset[str]] = frozenset()

        async def run(self, request: ReviewRequest) -> CaptureOutput:
            return CaptureOutput(
                tool="err_adapter", status="error", error="missing binary: semgrep",
                command=("err_adapter",),
            )

    monkeypatch.setitem(adapters_mod.REGISTRY, "ok_adapter", OkAdapter)
    monkeypatch.setitem(adapters_mod.REGISTRY, "err_adapter", ErrAdapter)

    runner = CliRunner()
    result = runner.invoke(
        app, ["run", "--analyzer", "ok_adapter", "--analyzer", "err_adapter", "--target", "."]
    )

    assert result.exit_code != 0
    # JSON parse succeeds iff no Python traceback polluted stdout
    by_tool = {o["tool"]: o for o in json.loads(result.output)["outputs"]}
    assert by_tool["ok_adapter"]["status"] == "ok"
    assert by_tool["err_adapter"]["status"] == "error"
    assert by_tool["err_adapter"]["error"]


def test_atomic_write_tmp_then_rename(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)
    monkeypatch.chdir(tmp_path)

    output_path = tmp_path / "result.json"
    runner = CliRunner()
    result = runner.invoke(
        app, ["run", "--analyzer", "fake", "--output", str(output_path), "--target", "."]
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert not (tmp_path / "result.json.tmp").exists()
    with output_path.open() as f:
        data = json.load(f)
    assert "outputs" in data and data["schema"] == "polyreview/review-bundle/v1"


def test_stdout_summary_only_when_output_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)
    monkeypatch.chdir(tmp_path)

    output_path = tmp_path / "result.json"
    runner = CliRunner()
    result = runner.invoke(
        app, ["run", "--analyzer", "fake", "--output", str(output_path), "--target", "."]
    )

    assert result.exit_code == 0, result.output
    summary = result.output.strip()
    # New thin-runner summary: analyzers count + per-status counts + total duration.
    assert re.match(r"analyzers: \d+ \| .*ok: \d+.* \| duration: .+s", summary), repr(summary)
    assert "{" not in result.output


@pytest.mark.parametrize("bad_path", [
    "/tmp/x.json",
    str(Path.home() / "x.json"),
    "/etc/x",
])
def test_output_outside_cwd_rejected_all_cases(bad_path: str) -> None:
    result = _run("--output", bad_path)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "sandbox" in combined.lower()
    assert not Path(bad_path).exists()


def test_cwd_guard_accepts_symlink_inside_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    link = tmp_path / "link"
    link.symlink_to(subdir)

    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app, ["run", "--analyzer", "fake", "--output", str(link / "result.json"), "--target", "."]
    )

    assert "sandbox" not in result.output.lower()


class _ScopeCapturingFake:
    name: ClassVar[str] = "fake"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    seen: ClassVar[list[str]] = []

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        type(self).seen.append(request.scope)
        return CaptureOutput(tool="fake", status="ok", command=("fake",))


def test_timing_scope_flows_into_request(monkeypatch: pytest.MonkeyPatch) -> None:
    _ScopeCapturingFake.seen = []
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", _ScopeCapturingFake)
    runner = CliRunner()

    result = runner.invoke(
        app, ["run", "--analyzer", "fake", "--target", ".", "--scope", "story-level"]
    )
    assert result.exit_code == 0, result.output
    assert _ScopeCapturingFake.seen == ["story-level"]

    _ScopeCapturingFake.seen = []
    result = runner.invoke(app, ["run", "--analyzer", "fake", "--target", "."])
    assert result.exit_code == 0, result.output
    assert _ScopeCapturingFake.seen == ["per-task"], "unset --scope must default to per-task"


def test_output_creates_missing_parent_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)
    monkeypatch.chdir(tmp_path)

    out = tmp_path / "sub" / "dir" / "result.json"
    runner = CliRunner()
    result = runner.invoke(
        app, ["run", "--analyzer", "fake", "--output", str(out), "--target", "."]
    )

    assert result.exit_code == 0, result.output
    assert out.exists()
    assert not (out.parent / "result.json.tmp").exists()


def test_cli_defaults_to_quick_whole_review_when_no_flags_given(tmp_path: Path) -> None:
    """Without --analyzer or --review/--depth the CLI defaults to --depth quick.

    Targets an isolated tmp dir (one small file) rather than '.': the real quick-review
    toolchain runs, but pointing it at the repo root would scan the vendored node_modules /
    .venv tree and take minutes. The assertion is about the *defaulting* (no old "required"
    error), so the target is incidental — a tiny controlled target keeps it fast and
    deterministic."""
    (tmp_path / "sample.py").write_text("x = 1\n")
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--target", str(tmp_path)])
    # Should succeed and produce JSON output (real tools run; exit code may be 1 if
    # any tool is unavailable, but the CLI must not exit with the old "required" error).
    assert "--analyzer or --language is required" not in result.output


def test_cli_auto_selects_adapters_from_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """--language python must auto-select adapters and run them."""
    from code_review.lang_select import select_adapters

    # Register a fake for every adapter lang_select would pick for python
    expected_adapters = select_adapters(frozenset({"python"}))
    for name in expected_adapters:
        # Create a unique class per name to avoid shared state
        cls = type(name, (FakeAnalyzer,), {"name": name})
        monkeypatch.setitem(adapters_mod.REGISTRY, name, cls)

    runner = CliRunner()
    result = runner.invoke(app, ["run", "--language", "python", "--target", "."])

    assert result.exit_code == 0, result.output
    assert set(expected_adapters) <= _tools(result.output)


def test_semgrep_rules_from_toml_reaches_request_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ADR-0016 #5: a `semgrep_rules` path in code-review.toml is threaded into
    request.config so the adapter can read it."""
    received: list[dict[str, object]] = []

    class ConfigCapturingFake:
        name = "fake"
        kind = "deterministic"
        default_timeout_s = 30
        scope_restrictions: frozenset[str] = frozenset()

        async def run(self, request: ReviewRequest) -> CaptureOutput:
            received.append(dict(request.config))
            return CaptureOutput(tool="fake", command=("fake",))

    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", ConfigCapturingFake)
    cfg = tmp_path / "code-review.toml"
    cfg.write_text('semgrep_rules = "/rules/security.yaml"\n')

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run", "--analyzer", "fake", "--target", str(tmp_path), "--config", str(cfg)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert received and received[0].get("semgrep_rules") == "/rules/security.yaml"
