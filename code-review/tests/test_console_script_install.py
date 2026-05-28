"""s1-t4: build the wheel, install into a clean venv, exercise the
claude-code-review console-script. Catches [project.scripts] regressions
before tagging."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


@pytest.mark.slow
def test_console_script_install(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()

    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    wheels = list(wheel_dir.glob("claude_code_review-*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    wheel_path = wheels[0]

    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
    )
    venv_python = venv_dir / "bin" / "python"

    subprocess.run(
        ["uv", "pip", "install", "--python", str(venv_python), str(wheel_path)],
        check=True,
        capture_output=True,
    )

    console_script = venv_dir / "bin" / "claude-code-review"
    assert console_script.exists(), (
        f"claude-code-review entry point missing at {console_script}"
    )

    installed = subprocess.run(
        [str(console_script), "--capabilities"],
        capture_output=True,
        text=True,
    )
    assert installed.returncode == 0, (
        f"installed console-script failed:\n{installed.stderr}"
    )
    installed_caps = json.loads(installed.stdout)
    assert "analyzers" in installed_caps, "installed --capabilities missing 'analyzers'"

    source = subprocess.run(
        [sys.executable, "-m", "code_review.cli", "--capabilities"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert source.returncode == 0, f"source --capabilities failed:\n{source.stderr}"
    source_caps = json.loads(source.stdout)

    for key in ("analyzers", "review_kinds", "stack_coverage"):
        assert installed_caps.get(key) == source_caps.get(key), (
            f"{key!r} mismatch between installed wheel and source tree:\n"
            f"  installed: {installed_caps.get(key)!r}\n"
            f"  source:    {source_caps.get(key)!r}"
        )
