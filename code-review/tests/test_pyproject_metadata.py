"""s1-t0: assert pyproject.toml carries the PyPI metadata fields required
for a polished package page."""
from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _project() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def test_name_is_polyreview() -> None:
    assert _project()["name"] == "polyreview"


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


def test_console_script_is_polyreview() -> None:
    scripts = _project()["scripts"]
    assert scripts == {"polyreview": "code_review.cli:app"}, (
        f"expected exactly the renamed console script; got {scripts}"
    )


def test_license_is_file_reference() -> None:
    """s2-t0: PyPI/PEP 639 expectation — license declares a file, not inline text.
    Inline `text = "MIT"` does not result in LICENSE shipping inside the wheel."""
    assert _project()["license"] == {"file": "LICENSE"}, (
        f"license must be file-based; got {_project()['license']}"
    )


def test_license_file_matches_repo_root_license() -> None:
    """s2-t0: code-review/LICENSE must be byte-identical to agentic-skills/LICENSE
    so the two never drift independently."""
    pkg_license = PYPROJECT.parent / "LICENSE"
    repo_license = PYPROJECT.parent.parent / "LICENSE"
    assert pkg_license.exists(), f"code-review/LICENSE missing at {pkg_license}"
    assert repo_license.exists(), f"agentic-skills/LICENSE missing at {repo_license}"
    assert pkg_license.read_bytes() == repo_license.read_bytes(), (
        "code-review/LICENSE drifted from agentic-skills/LICENSE"
    )


def test_runtime_dependencies_disallow_exact_pin() -> None:
    """s2-t1 + ADR-0013: runtime deps in PyPI-published packages must not exact-pin.
    Lower-bound-only (>=X.Y). Upper bounds are permitted iff the dep line in the raw
    TOML carries an inline `#` comment justifying the cap."""
    deps = _project()["dependencies"]
    assert deps, "dependencies list must be non-empty"
    for spec in deps:
        assert ">=" in spec, f"dep must use >= lower bound; got {spec!r}"
        assert "==" not in spec, f"dep must not use == exact pin; got {spec!r}"
        assert "~=" not in spec, f"dep must not use ~= compatible release; got {spec!r}"

    raw = PYPROJECT.read_text(encoding="utf-8")
    for spec in deps:
        if "<" not in spec:
            continue
        line = next(
            (ln for ln in raw.splitlines() if spec in ln),
            None,
        )
        assert line is not None, (
            f"could not locate raw TOML line for capped dep {spec!r}; cannot verify justification"
        )
        assert "#" in line, (
            f"capped dep {spec!r} requires inline `#` justification on its TOML line; got: {line!r}"
        )


def test_runtime_dependency_set_matches_expected() -> None:
    """s2-t1 + ADR-0013: hardcoded full set. Drift to a lower minor, drift to patch-level
    anchoring, or addition/removal of a dep without updating this test all trip the assertion."""
    expected = {
        "typer>=0.18",
        "jsonschema>=4.26",
        "bandit>=1.7",
        "radon>=6.0",
        "vulture>=2.13",
        "pydeps>=1.12",
        "cohesion>=1.1",
        "schemathesis>=4.0,<5",
    }
    actual = set(_project()["dependencies"])
    assert actual == expected, (
        f"dependency set drifted; missing={sorted(expected - actual)}, "
        f"unexpected={sorted(actual - expected)}"
    )
