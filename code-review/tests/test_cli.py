import json
import subprocess
import sys
from pathlib import Path


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
