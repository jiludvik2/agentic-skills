"""Production-layout end-to-end smoke per s0-t3.

Stages the nested production layout under tmp_path
(`<tmp>/.claude/skills/code-review/code_review/...`) and exercises the CLI
end-to-end via subprocess with cwd=<tmp> and PYTHONPATH pointing at the
staged skill_root. Proves: importlib.resources package-data loading, CWD-
relative code-review.toml lookup, and CLI/analyzer plumbing all work when
the Python package is nested inside `.claude/skills/code-review/`."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SUBPROJECT_ROOT = Path(__file__).parent.parent
SRC_PKG = SUBPROJECT_ROOT / "code_review"
SKILL_MD = SUBPROJECT_ROOT / ".claude" / "skills" / "code-review" / "SKILL.md"


def _stage_production_layout(tmp_path: Path) -> Path:
    """Copy the source-tree code_review/ into a nested skill-root layout
    under tmp_path and return the skill_root path."""
    skill_root = tmp_path / ".claude" / "skills" / "code-review"
    skill_root.mkdir(parents=True)
    if SKILL_MD.exists():
        shutil.copy2(SKILL_MD, skill_root / "SKILL.md")
    shutil.copytree(
        SRC_PKG,
        skill_root / "code_review",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return skill_root


def _run_cli(args: list[str], cwd: Path, skill_root: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(skill_root)}
    return subprocess.run(
        [sys.executable, "-m", "code_review.cli", "run", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.slow
def test_production_layout_capabilities_works(tmp_path: Path) -> None:
    skill_root = _stage_production_layout(tmp_path)
    result = _run_cli(["--capabilities"], cwd=tmp_path, skill_root=skill_root)
    assert result.returncode == 0, (
        f"--capabilities failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    data = json.loads(result.stdout)
    assert "analyzers" in data, f"--capabilities missing 'analyzers' key; keys={list(data)}"


@pytest.mark.slow
def test_production_layout_review_runs_against_fixture(tmp_path: Path) -> None:
    skill_root = _stage_production_layout(tmp_path)
    fixture = tmp_path / "sample.py"
    fixture.write_text("import subprocess\nsubprocess.call('ls', shell=True)\n")

    result = _run_cli(
        ["--analyzer", "bandit", "--target", "."],
        cwd=tmp_path,
        skill_root=skill_root,
    )
    assert result.returncode == 0, (
        f"--analyzer bandit failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    payload = json.loads(result.stdout)
    tools = {o["tool"] for o in payload["outputs"]}
    assert "bandit" in tools, f"bandit not in bundle outputs; tools={tools}"


@pytest.mark.slow
def test_production_layout_cwd_toml_is_honored(tmp_path: Path) -> None:
    """If `disabled_analyzers = ['semgrep']` lives in CWD's code-review.toml,
    the CLI must refuse to run `--analyzer semgrep`. Proves the staged layout
    found and parsed the CWD-relative TOML."""
    skill_root = _stage_production_layout(tmp_path)
    (tmp_path / "code-review.toml").write_text('disabled_analyzers = ["semgrep"]\n')

    result = _run_cli(
        ["--analyzer", "semgrep", "--target", "."],
        cwd=tmp_path,
        skill_root=skill_root,
    )
    assert result.returncode != 0, "CLI should refuse a disabled analyzer"
    assert "disabled in code-review.toml" in (result.stderr or result.stdout), (
        f"missing 'disabled in code-review.toml' guard:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
