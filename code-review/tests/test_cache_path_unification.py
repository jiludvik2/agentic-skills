"""s0-t6: a single resolver owns the cache base directory, consumed by both
the producer (scripts/prefetch_caches.py) and the consumers (trivy/js_base).
Guards against the producer/consumer path divergence that previously existed
(producer wrote SKILL_ROOT-relative, consumers read CWD-relative)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from code_review.paths import cache_root, node_modules_dir, trivy_cache_dir

_PREFETCH = Path(__file__).parent.parent / "scripts" / "prefetch_caches.py"


def _load_prefetch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prefetch_caches", _PREFETCH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cache_root_defaults_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POLYREVIEW_CACHE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cache_root() == tmp_path / ".claude" / "skills" / "code-review"


def test_cache_root_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path / "custom"))
    assert cache_root() == tmp_path / "custom"


def test_trivy_and_node_derive_from_cache_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    assert trivy_cache_dir() == tmp_path / "cache" / "trivy-db"
    assert node_modules_dir() == tmp_path / "node_modules"


def test_consumer_reads_under_producer_cache_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The trivy DB the consumer reads lives under the same ``cache/`` dir the
    producer writes; node_modules sits directly under cache_root()."""
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    assert trivy_cache_dir().parent == cache_root() / "cache"
    assert node_modules_dir().parent == cache_root()


def test_producer_writes_manifest_under_cache_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running the producer leaves its manifest under cache_root()/cache —
    the exact tree the consumers resolve against."""
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)  # prove it does NOT depend on CWD when env set
    prefetch = _load_prefetch()
    rc = prefetch.main()
    assert rc == 0
    assert (cache_root() / "cache" / "manifest.json").exists()


async def test_trivy_cache_absent_error_is_layout_agnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wheel-installed-no-producer layout: the cache is simply absent and no
    setup.sh ships. The error must offer the env-override path, not only tell the
    operator to run a script that may not exist."""
    from unittest.mock import patch

    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))  # no cache/trivy-db under it
    request = ReviewRequest(
        scope="per-task", diff_range=None, target_paths=(".",),
        languages=frozenset(), config={},
    )
    # trivy on PATH so the pre-flight reaches the DB check (a provisioning gap → unavailable
    # per ADR-0019, not error); the reason must still offer the env-override path.
    with patch("code_review.adapters.trivy.shutil.which", return_value="/usr/bin/trivy"):
        output = await TrivyAdapter().run(request)
    assert output.status == "unavailable"
    assert output.error is not None
    assert "POLYREVIEW_CACHE_DIR" in output.error
    assert str(trivy_cache_dir()) in output.error


# The resolver collapses the three deployment layouts (dev-sibling, production-nested,
# wheel-installed) into exactly two anchoring branches: the CWD-anchored default and the
# $POLYREVIEW_CACHE_DIR override. dev-sibling + production-nested differ only by which CWD
# the CLI runs from (the cwd-anchored case below); wheel-installed has no producer and is
# covered by the layout-agnostic cache-absent error test above.
@pytest.mark.parametrize(
    "set_env",
    [False, True],
    ids=["cwd-anchored", "env-anchored"],
)
def test_producer_consumer_agree_across_layouts(
    set_env: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Under either anchoring mode, the producer's cache dir and the consumers'
    read paths resolve to one coherent tree."""
    if set_env:
        monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path / "anchor"))
    else:
        monkeypatch.delenv("POLYREVIEW_CACHE_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
    prefetch = _load_prefetch()
    producer_cache = prefetch.prefetch_cache_dir()
    assert producer_cache == cache_root() / "cache"
    assert trivy_cache_dir().is_relative_to(producer_cache)
    assert node_modules_dir().is_relative_to(cache_root())
