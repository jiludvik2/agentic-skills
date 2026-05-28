"""s1-t0: assert pyproject.toml carries the PyPI metadata fields required
for a polished package page."""
from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _project() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def test_name_is_claude_code_review() -> None:
    assert _project()["name"] == "claude-code-review"


def test_version_is_set() -> None:
    assert _project()["version"], "version must be non-empty"


def test_requires_python_floor_311() -> None:
    assert _project()["requires-python"] == ">=3.11"


def test_description_is_non_empty() -> None:
    assert _project()["description"], "description must be non-empty"


def test_authors_present_no_email() -> None:
    authors = _project()["authors"]
    assert authors, "authors must be non-empty"
    assert all("name" in a for a in authors), "every author must have a name"
    assert all("email" not in a for a in authors), (
        "author emails are intentionally omitted per task spec"
    )


def test_readme_points_at_readme_md() -> None:
    assert _project()["readme"] == "README.md"


def test_readme_file_exists_and_non_empty() -> None:
    readme = PYPROJECT.parent / _project()["readme"]
    assert readme.exists(), f"readme file not found at {readme}"
    assert readme.read_text(encoding="utf-8").strip(), "readme file must be non-empty"


def test_project_urls_present() -> None:
    urls = _project()["urls"]
    for key in ("Homepage", "Source", "Issues"):
        assert key in urls and urls[key], f"missing project URL: {key}"


def test_required_classifiers_present() -> None:
    classifiers = _project()["classifiers"]
    required = {
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha",
    }
    missing = required - set(classifiers)
    assert not missing, f"missing classifiers: {sorted(missing)}"


def test_keywords_present() -> None:
    keywords = _project()["keywords"]
    expected = [
        "code-review", "sarif", "static-analysis",
        "semgrep", "bandit", "sdlc", "deterministic-analyzer",
    ]
    for kw in expected:
        assert kw in keywords, f"missing keyword: {kw}"


def test_console_script_is_claude_code_review() -> None:
    scripts = _project()["scripts"]
    assert scripts == {"claude-code-review": "code_review.cli:app"}, (
        f"expected exactly the renamed console script; got {scripts}"
    )
