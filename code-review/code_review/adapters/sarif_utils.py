from __future__ import annotations

from pathlib import Path
from typing import Any

_SARIF_SCHEMA_URI = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
)


def normalise_sarif(sarif: dict[str, Any]) -> dict[str, Any]:
    if "version" not in sarif:
        sarif = {"version": "2.1.0", **sarif}
    if "$schema" not in sarif:
        sarif = {"$schema": _SARIF_SCHEMA_URI, **sarif}
    return sarif


def empty_sarif(tool_name: str, tool_version: str = "0.0.0") -> dict[str, Any]:
    return {
        "$schema": _SARIF_SCHEMA_URI,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {"name": tool_name, "version": tool_version, "rules": []}
                },
                "results": [],
            }
        ],
    }


def make_location(uri: str, start_line: int = 1) -> dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {"uri": uri},
            "region": {"startLine": start_line},
        }
    }


def rel_uri(path: str | Path, root: str | Path | None = None) -> str:
    """Return path as a string relative to root (CWD if None), or absolute str on failure."""
    p = Path(path)
    base = Path(root) if root is not None else Path.cwd()
    try:
        return str(p.relative_to(base))
    except ValueError:
        return str(p)


def collect_python_files(paths: tuple[str, ...]) -> list[Path]:
    """Collect .py files from a mix of directory and file paths."""
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(p.rglob("*.py"))
        elif p.suffix == ".py" and p.is_file():
            files.append(p)
    return files
