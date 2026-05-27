import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_package_importable():
    import code_review

    assert isinstance(code_review.__version__, str)


def test_pyproject_valid():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    project = data["project"]
    assert project["name"] == "code-review"
    assert project["requires-python"].startswith(">=3.11")
    assert data["build-system"]["build-backend"] == "hatchling.build"
    scripts = project.get("scripts", {})
    assert scripts.get("code-review") == "code_review.cli:app"


def test_sarif_schema_present_and_valid():
    schema_path = REPO_ROOT / "code_review" / "schemas" / "sarif-2.1.0.json"
    assert schema_path.exists(), f"SARIF schema not found at {schema_path}"
    schema = json.loads(schema_path.read_text())
    assert "$schema" in schema or "title" in schema


def test_gitignore_covers_transient_dirs():
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    for entry in ("runs/", "cache/", "node_modules/", ".venv/"):
        assert entry in gitignore, f"Missing {entry!r} in .gitignore"
