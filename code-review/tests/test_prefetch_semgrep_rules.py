"""s0-t1: prefetch_caches.py provisions the vendored semgrep ruleset into the
runtime cache (cache_root()/cache/semgrep/rules), idempotently. The vendored
source lives in the skill bundle (.claude/skills/code-review/semgrep-rules)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from code_review.paths import cache_root

_PREFETCH = Path(__file__).parent.parent / "scripts" / "prefetch_caches.py"
_BUNDLED_RULES = (
    Path(__file__).parent.parent
    / ".claude" / "skills" / "code-review" / "semgrep-rules"
)


def _load_prefetch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prefetch_caches", _PREFETCH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_vendored_ruleset_exists_in_bundle() -> None:
    """The canonical vendored ruleset is committed in the skill bundle."""
    assert _BUNDLED_RULES.is_dir(), f"missing vendored ruleset: {_BUNDLED_RULES}"
    assert list(_BUNDLED_RULES.glob("*.y*ml")), "vendored ruleset has no rule files"


def test_prefetch_provisions_semgrep_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    rules_dir = cache_root() / "cache" / "semgrep" / "rules"
    assert not rules_dir.exists()

    rc = _load_prefetch().main()

    assert rc == 0
    assert rules_dir.is_dir()
    provisioned = sorted(p.name for p in rules_dir.glob("*.y*ml"))
    expected = sorted(p.name for p in _BUNDLED_RULES.glob("*.y*ml"))
    assert provisioned == expected, f"expected {expected}, got {provisioned}"


def test_prefetch_semgrep_rules_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    prefetch = _load_prefetch()

    assert prefetch.main() == 0
    rules_dir = cache_root() / "cache" / "semgrep" / "rules"
    first = {p.name: p.read_text(encoding="utf-8") for p in rules_dir.glob("*.y*ml")}

    # Second run must not error and must leave the rule files byte-identical.
    assert prefetch.main() == 0
    second = {p.name: p.read_text(encoding="utf-8") for p in rules_dir.glob("*.y*ml")}
    assert first == second
