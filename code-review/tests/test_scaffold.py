import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_package_importable() -> None:
    import code_review

    assert isinstance(code_review.__version__, str)


def test_pyproject_valid() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    project = data["project"]
    assert project["name"] == "polyreview"
    assert project["requires-python"].startswith(">=3.11")
    assert data["build-system"]["build-backend"] == "hatchling.build"
    scripts = project.get("scripts", {})
    assert scripts.get("polyreview") == "code_review.cli:app"


def test_sarif_schema_absent() -> None:
    """sarif-2.1.0.json was removed in s2-t1; it must not be re-added without a loader."""
    schema_path = REPO_ROOT / "code_review" / "schemas" / "sarif-2.1.0.json"
    assert not schema_path.exists()


def test_readme_exists() -> None:
    readme = REPO_ROOT / "README.md"
    assert readme.exists(), f"README.md not found at {readme}"
    assert readme.read_text(encoding="utf-8").strip(), "README.md must be non-empty"


def test_adr_0012_pypi_publication_exists() -> None:
    """ADR-0012 lives under sdlc/work/active/ until story close, then moves
    to sdlc/docs/decisions/. Accept either location."""
    candidates = [
        REPO_ROOT / "sdlc" / "work" / "active" / "adr-0012-pypi-publication.md",
        REPO_ROOT / "sdlc" / "docs" / "decisions" / "adr-0012-pypi-publication.md",
    ]
    assert any(p.exists() for p in candidates), (
        f"ADR-0012 not found in either expected location: {[str(p) for p in candidates]}"
    )


def test_release_runbook_exists() -> None:
    """Release runbook lives under sdlc/work/active/release-runbook.md until
    story close, then moves+renames to sdlc/docs/runbooks/release.md."""
    candidates = [
        REPO_ROOT / "sdlc" / "work" / "active" / "release-runbook.md",
        REPO_ROOT / "sdlc" / "docs" / "runbooks" / "release.md",
    ]
    assert any(p.exists() for p in candidates), (
        f"release runbook not found in either expected location: {[str(p) for p in candidates]}"
    )


def test_gitignore_covers_transient_dirs() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    for entry in ("runs/", "cache/", "node_modules/", ".venv/"):
        assert entry in gitignore, f"Missing {entry!r} in .gitignore"
