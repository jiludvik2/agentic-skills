"""Verify that uv build produces a wheel with all bundled JSON files intact,
and that a fresh-venv install exposes them via importlib.resources."""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from code_review.bundle import (
    BUNDLE_DIRS,
    BUNDLE_EXCLUDED,
    BUNDLE_FILES,
    BUNDLE_ROOT,
)

REPO_ROOT = Path(__file__).parent.parent

_EXPECTED_IN_WHEEL = [
    "code_review/capabilities.json",
    "code_review/schemas/capabilities.json",
    "code_review/schemas/review-request.json",
    "code_review/schemas/review-bundle.v1.json",
    "code_review/schemas/sarif-2.1.0.json",
]


def _build_wheel(tmp_path: Path) -> Path:
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
    return wheels[0]


@pytest.mark.slow
def test_wheel_contains_bundled_json(tmp_path: Path) -> None:
    wheel_path = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()
    for expected in _EXPECTED_IN_WHEEL:
        assert any(n == expected for n in names), (
            f"{expected!r} missing from wheel; wheel contains: {sorted(names)}"
        )


@pytest.mark.slow
def test_wheel_contains_license_file(tmp_path: Path) -> None:
    """s2-t0: the built wheel must carry the LICENSE inside its dist-info,
    regardless of Hatchling's exact PEP 639 sub-path (`dist-info/LICENSE` vs
    `dist-info/licenses/LICENSE`)."""
    wheel_path = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    matches = [
        n for n in names
        if n.endswith("LICENSE") and ".dist-info/" in n
    ]
    assert matches, (
        f"no LICENSE file in wheel dist-info; wheel contains: {sorted(names)}"
    )


@pytest.mark.slow
def test_wheel_contains_skill_bundle(tmp_path: Path) -> None:
    """s6-t1: every BUNDLE_MANIFEST asset is force-included under
    ``code_review/<BUNDLE_ROOT>/`` so the install command can read it via
    importlib.resources over the package."""
    wheel_path = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())

    prefix = f"code_review/{BUNDLE_ROOT}"
    for asset in BUNDLE_FILES:
        expected = f"{prefix}/{asset}"
        assert expected in names, (
            f"{expected!r} missing from wheel; wheel contains: {sorted(names)}"
        )
    for bundle_dir in BUNDLE_DIRS:
        dir_prefix = f"{prefix}/{bundle_dir}/"
        # A non-empty directory — at least one real file under it, not just the
        # dir entry — so a wrong/empty force-include can't pass silently.
        assert any(
            n.startswith(dir_prefix) and not n.endswith("/") for n in names
        ), f"no files under {dir_prefix!r}; wheel contains: {sorted(names)}"

    # Drift guard, the other direction: every top-level entry the wheel ships under
    # _bundle/ must map back to a BUNDLE_MANIFEST name — catches a force-include
    # line in pyproject.toml that the manifest does not declare (single-source check).
    manifest = set(BUNDLE_FILES) | set(BUNDLE_DIRS)
    shipped_tops = {
        n[len(prefix) + 1 :].split("/", 1)[0]
        for n in names
        if n.startswith(f"{prefix}/") and n != f"{prefix}/"
    }
    assert shipped_tops <= manifest, (
        f"wheel ships _bundle entries not in BUNDLE_MANIFEST: {shipped_tops - manifest}"
    )


@pytest.mark.slow
def test_wheel_excludes_provisioned_dirs(tmp_path: Path) -> None:
    """s6-t1: node_modules/, cache/, runs/ are host-provisioned/produced and must
    never be shipped in the wheel (guards against force-including the whole
    `.claude/skills/code-review/` tree)."""
    wheel_path = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    prefix = f"code_review/{BUNDLE_ROOT}"
    for excluded in BUNDLE_EXCLUDED:
        leak = [n for n in names if n.startswith(f"{prefix}/{excluded}")]
        assert not leak, f"provisioned dir {excluded!r} leaked into wheel: {leak}"


@pytest.mark.slow
def test_wheel_installed_bundle_importable(tmp_path: Path) -> None:
    """s6-t1: from an installed wheel, importlib.resources locates the bundle
    SKILL.md under the package — the resolution mechanism the install command uses."""
    wheel_path = _build_wheel(tmp_path)
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

    snippet = (
        "import importlib.resources as r;"
        "from code_review.bundle import BUNDLE_ROOT;"
        "p = r.files('code_review').joinpath(BUNDLE_ROOT, 'SKILL.md');"
        "print(p.is_file())"
    )
    result = subprocess.run(
        [str(venv_python), "-c", snippet],
        capture_output=True,
        text=True,
        # Run from tmp_path so CWD (sys.path[0]) cannot shadow the installed
        # package with the repo's source `code_review/` (which lacks _bundle/).
        cwd=tmp_path,
    )
    assert result.returncode == 0, f"importlib resolution failed:\n{result.stderr}"
    assert result.stdout.strip() == "True", (
        f"SKILL.md not resolvable from installed package: {result.stdout!r}"
    )


@pytest.mark.slow
def test_wheel_installed_capabilities_accessible(tmp_path: Path) -> None:
    wheel_path = _build_wheel(tmp_path)
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
        [str(venv_python), "-m", "code_review.cli", "run", "--capabilities"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"--capabilities failed:\n{result.stderr}"
    data = json.loads(result.stdout)
    assert "analyzers" in data, "--capabilities output missing 'analyzers' key"
