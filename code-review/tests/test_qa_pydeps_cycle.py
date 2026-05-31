"""In-sandbox integration test for the pydeps precision oracle (s5-t1).

pydeps is pure-Python (no node/brew/network), so this runs the *real* tool against the
labelled `cyclepkg` coupling fixture and asserts the precision oracle detects the planted
`a → b → a` import cycle. This is the one automated real-tool proof of a precision oracle
that fits inside the sandbox; depcruiser's equivalent (node-dependent) is covered by the
manually-run full harness in s5-t2.

Marked `integration` (needs the `pydeps` console entry point importable in the venv).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_QA = (
    Path(__file__).resolve().parents[1]
    / "sdlc"
    / "docs"
    / "qa"
    / "analyzer-coverage"
)
_ORACLE_PATH = _QA / "bundle_oracle.py"
_CYCLEPKG_PARENT = _QA / "fixtures" / "python"
_CYCLEPKG = _CYCLEPKG_PARENT / "cyclepkg"


def _load_oracle() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qa_bundle_oracle", _ORACLE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cyclepkg_fixture_plants_the_cycle() -> None:
    """The fixture is the contract: a/b must import each other. A scaffold edit that drops
    the planted back-edge fails here, loudly."""
    a = (_CYCLEPKG / "a.py").read_text(encoding="utf-8")
    b = (_CYCLEPKG / "b.py").read_text(encoding="utf-8")
    assert "import b" in a or "cyclepkg import b" in a or "cyclepkg.b" in a
    assert "import a" in b or "cyclepkg import a" in b or "cyclepkg.a" in b


@pytest.mark.integration
def test_pydeps_detects_planted_cycle() -> None:
    """Run real pydeps on the cyclepkg fixture (the adapter's exact invocation) and assert
    the precision oracle finds the mutual back-edge cyclepkg.a ↔ cyclepkg.b."""
    oracle = _load_oracle()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pydeps",
            "cyclepkg",
            "--show-deps",
            "--no-output",
            "--noshow",
        ],
        cwd=str(_CYCLEPKG_PARENT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"pydeps failed: {proc.stderr[:400]}"
    # The oracle reads the raw stdout exactly as it would from the bundle.
    assert oracle.pydeps_has_cycle(proc.stdout, "cyclepkg.a", "cyclepkg.b") is True
    # Sanity: the graph really does carry the dotted module keys.
    graph = json.loads(proc.stdout)
    assert "cyclepkg.a" in graph and "cyclepkg.b" in graph
