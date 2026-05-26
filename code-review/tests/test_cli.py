import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.cli import app
from tests.conftest import FakeAnalyzer, FakeAnalyzer2, SlowFakeAnalyzer


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "code_review.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_help_exits_zero():
    result = _run("--help")
    assert result.returncode == 0
    assert "--analyzer" in result.stdout
    assert "--output" in result.stdout


def test_capabilities_stub_exits_zero():
    result = _run("--capabilities")
    assert result.returncode == 0
    json.loads(result.stdout)


def test_output_tmp_rejected():
    result = _run("--output", "/tmp/x.json")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "sandbox" in combined.lower() or "cwd" in combined.lower()
    assert not Path("/tmp/x.json").exists()


def test_output_home_rejected():
    path = str(Path.home() / "review.json")
    result = _run("--output", path)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "sandbox" in combined.lower() or "cwd" in combined.lower()
    assert not Path(path).exists()


def test_output_etc_rejected():
    result = _run("--output", "/etc/review.json")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "sandbox" in combined.lower() or "cwd" in combined.lower()
    assert not Path("/etc/review.json").exists()


def test_concurrent_execution_faster_than_sequential(monkeypatch: pytest.MonkeyPatch):
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
    result = runner.invoke(app, ["--analyzer", "slow1", "--analyzer", "slow2", "--target", "."])
    elapsed = time.monotonic() - start

    assert result.exit_code == 0, result.output
    assert elapsed < 0.35, f"Elapsed {elapsed:.3f}s suggests sequential execution"


def test_consolidated_output_shape(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake2", FakeAnalyzer2)

    runner = CliRunner()
    result = runner.invoke(app, ["--analyzer", "fake", "--analyzer", "fake2", "--target", "."])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "fake" in data["analyzers"]
    assert "fake2" in data["analyzers"]


def test_diff_scope_excludes_unchanged_files(monkeypatch: pytest.MonkeyPatch):
    received_paths: list[tuple[str, ...]] = []

    class PathCapturingFake:
        name = "fake"
        kind = "deterministic"
        default_timeout_s = 30
        scope_restrictions: frozenset[str] = frozenset()

        async def run(self, request: object) -> object:
            from code_review.contracts import AnalyzerOutput, ReviewRequest
            assert isinstance(request, ReviewRequest)
            received_paths.append(request.target_paths)
            return AnalyzerOutput(sarif={})

    async def _mock_resolve(repo_root: object, diff_range: object) -> tuple[str, ...]:
        return ("changed.py",)

    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", PathCapturingFake)
    monkeypatch.setattr("code_review.cli.resolve_diff_paths", _mock_resolve)

    runner = CliRunner()
    result = runner.invoke(app, ["--analyzer", "fake", "--diff", "HEAD~1..HEAD"])

    assert result.exit_code == 0, result.output
    assert received_paths == [("changed.py",)], f"Expected only changed.py; got {received_paths}"
    assert "unchanged.py" not in str(result.output)
