"""Verify that uv build produces a wheel with all bundled JSON files intact,
and that a fresh-venv install exposes them via importlib.resources."""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

_EXPECTED_IN_WHEEL = [
    "code_review/capabilities.json",
    "code_review/schemas/capabilities.json",
    "code_review/schemas/review-request.json",
    "code_review/schemas/review-response.json",
    "code_review/schemas/sarif-2.1.0.json",
]


@pytest.mark.slow
def test_wheel_contains_bundled_json(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()

    subprocess.run(
        ["uv", "build", "--out-dir", str(wheel_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )

    wheels = list(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    wheel_path = wheels[0]

    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()
    for expected in _EXPECTED_IN_WHEEL:
        assert any(n == expected for n in names), (
            f"{expected!r} missing from wheel; wheel contains: {sorted(names)}"
        )


@pytest.mark.slow
def test_wheel_installed_capabilities_accessible(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()

    subprocess.run(
        ["uv", "build", "--out-dir", str(wheel_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )

    wheel_path = next(wheel_dir.glob("*.whl"))
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

    result = subprocess.run(
        [str(venv_python), "-m", "code_review.cli", "--capabilities"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"--capabilities failed:\n{result.stderr}"
    data = json.loads(result.stdout)
    assert "analyzers" in data, "--capabilities output missing 'analyzers' key"
