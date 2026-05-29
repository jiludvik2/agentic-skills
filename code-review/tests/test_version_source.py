"""s2-t2: ensure code_review.__version__ is read from installed package
metadata, not hardcoded as a string literal."""
from __future__ import annotations

import importlib
import importlib.metadata
import re
from pathlib import Path
from typing import NoReturn

import pytest

INIT_PATH = Path(__file__).parent.parent / "code_review" / "__init__.py"
# Matches semver literals in either quote style; future "quick fix"
# re-introductions are caught regardless of whether the developer types
# "0.1.0" or '0.1.0'.
_SEMVER_LITERAL = re.compile(r'''["']\d+\.\d+\.\d+(?:[+-][\w.]+)?["']''')


def test_version_matches_installed_package_metadata() -> None:
    import code_review

    assert code_review.__version__ == importlib.metadata.version("claude-code-review"), (
        f"__version__ ({code_review.__version__!r}) drifted from "
        f"installed metadata ({importlib.metadata.version('claude-code-review')!r})"
    )


def test_no_hardcoded_version_in_init() -> None:
    source = INIT_PATH.read_text(encoding="utf-8")
    matches = [
        m.group(0) for m in _SEMVER_LITERAL.finditer(source)
        if m.group(0) not in ('"0.0.0+dev"', "'0.0.0+dev'")
    ]
    assert not matches, (
        f"hardcoded version literal(s) found in __init__.py: {matches}; "
        "version must come from importlib.metadata.version()"
    )


def test_fallback_returned_when_metadata_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_missing(_: str) -> NoReturn:
        raise importlib.metadata.PackageNotFoundError("claude-code-review")

    import code_review

    try:
        monkeypatch.setattr(importlib.metadata, "version", _raise_missing)
        importlib.reload(code_review)
        assert code_review.__version__ == "0.0.0+dev", (
            f"expected dev sentinel; got {code_review.__version__!r}"
        )
    finally:
        # Order matters: pytest's auto-undo of monkeypatch runs at fixture
        # teardown (after this function returns), so the patch is still
        # active here. Undo manually before the reload, else the reload
        # re-executes the module body while `version` still raises and
        # caches the sentinel as code_review.__version__ for downstream
        # tests in the same session.
        monkeypatch.undo()
        importlib.reload(code_review)
