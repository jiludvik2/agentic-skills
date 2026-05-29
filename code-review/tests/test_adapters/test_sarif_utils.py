# tests/test_adapters/test_sarif_utils.py
from pathlib import Path

from code_review.adapters.sarif_utils import (
    collect_python_files,
    empty_sarif,
    make_location,
    normalise_sarif,
    rel_uri,
)

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"


def test_normalise_sarif_adds_version_and_schema() -> None:
    result = normalise_sarif({"runs": []})
    assert result["version"] == "2.1.0"
    assert "$schema" in result
    assert "runs" in result


def test_normalise_sarif_preserves_existing() -> None:
    sarif = {"version": "2.1.0", "$schema": "x", "runs": []}
    assert normalise_sarif(sarif) == sarif


def test_empty_sarif_structure() -> None:
    s = empty_sarif("mytool", "1.2.3")
    assert s["version"] == "2.1.0"
    runs = s["runs"]
    assert len(runs) == 1
    assert runs[0]["tool"]["driver"]["name"] == "mytool"
    assert runs[0]["tool"]["driver"]["version"] == "1.2.3"
    assert runs[0]["results"] == []


def test_make_location() -> None:
    loc = make_location("src/foo.py", 42)
    assert loc["physicalLocation"]["artifactLocation"]["uri"] == "src/foo.py"
    assert loc["physicalLocation"]["region"]["startLine"] == 42


def test_rel_uri_relative_to_cwd(tmp_path: Path) -> None:
    child = tmp_path / "sub" / "file.py"
    assert rel_uri(child, tmp_path) == "sub/file.py"


def test_rel_uri_outside_root_returns_str(tmp_path: Path) -> None:
    other = Path("/other/path.py")
    result = rel_uri(other, tmp_path)
    assert "other/path.py" in result


def test_collect_python_files() -> None:
    files = collect_python_files((str(_FIXTURE),))
    names = [f.name for f in files]
    assert "main.py" in names
    assert "complex.py" in names
