import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock

import jsonschema
import pytest

from code_review.adapters.base import SubprocessResult

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"
RULES_PATH = Path(__file__).parent.parent / "fixtures" / "semgrep-rules"


def test_semgrep_protocol_conformance() -> None:
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import Analyzer

    adapter = SemgrepAdapter()
    assert isinstance(adapter, Analyzer)
    assert SemgrepAdapter.name == "semgrep"


@pytest.mark.integration
async def test_semgrep_produces_valid_sarif() -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep not on PATH")

    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE_PATH),),
        languages=frozenset({"python"}),
        config={"semgrep_rules": str(RULES_PATH)},
    )
    output = await SemgrepAdapter().run(request)

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(output.sarif, schema)

    results = output.sarif.get("runs", [{}])[0].get("results", [])
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("subprocess-shell-true" in rid for rid in rule_ids), (
        f"Expected subprocess-shell-true finding; got rule IDs: {rule_ids}"
    )


async def test_semgrep_missing_binary_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    monkeypatch.setattr(
        "asyncio.create_subprocess_exec",
        AsyncMock(side_effect=FileNotFoundError("semgrep: No such file or directory")),
    )

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(".",),
        languages=frozenset({"python"}),
        config={},
    )
    output = await SemgrepAdapter().run(request)

    assert output.status == "error"
    assert output.error is not None and len(output.error) > 0


async def test_base_subprocess_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from code_review.adapters.base import run_subprocess

    class _HangingProcess:
        returncode = None
        pid = 99999

        async def communicate(self) -> tuple[bytes, bytes]:
            await asyncio.sleep(9999)
            return b"", b""

        def kill(self) -> None:
            pass

    async def _hanging(*args: object, **kwargs: object) -> _HangingProcess:
        return _HangingProcess()

    monkeypatch.setattr("asyncio.create_subprocess_exec", _hanging)

    result = await run_subprocess("semgrep", "--version", timeout_s=0.05)

    assert result.timed_out is True


def _capture_run(
    captured: list[tuple[object, ...]],
    *,
    stdout: bytes = b'{"runs": []}',
    returncode: int = 0,
) -> object:
    """Build a run_subprocess stub that records its positional argv (the
    semgrep command) and returns a canned SubprocessResult."""

    async def _run(*args: object, **kwargs: object) -> SubprocessResult:
        captured.append(args)
        return SubprocessResult(stdout=stdout, stderr=b"", returncode=returncode)

    return _run


async def test_semgrep_rules_dir_honors_cache_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    rules = tmp_path / "cache" / "semgrep" / "rules"
    rules.mkdir(parents=True)
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))

    captured: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "code_review.adapters.semgrep.run_subprocess", _capture_run(captured)
    )

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(".",),
        languages=frozenset({"python"}),
        config={},
    )
    await SemgrepAdapter().run(request)

    assert captured, "run_subprocess was not called"
    argv = captured[0]
    assert "--config" in argv
    config_arg = argv[argv.index("--config") + 1]
    assert config_arg == str(rules), f"--config should point at cache dir; got {config_arg}"


async def test_semgrep_missing_cache_returns_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    # Empty cache root: no provisioned rules and no override.
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))

    called: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "code_review.adapters.semgrep.run_subprocess", _capture_run(called)
    )

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(".",),
        languages=frozenset({"python"}),
        config={},
    )
    output = await SemgrepAdapter().run(request)

    assert output.status == "error"
    assert output.error is not None
    assert "setup.sh" in output.error, f"error must name setup.sh; got: {output.error}"
    # The broken `--config auto` + `--metrics off` combination must never run.
    for argv in called:
        assert not ("auto" in argv and "off" in argv), (
            "must not emit --config auto together with --metrics off"
        )


async def test_semgrep_keeps_x_ignore_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # ADR-0016 scenario 3: the flag is NOT removed — it is load-bearing. Without
    # it, semgrep's default .semgrepignore excludes tests/ and findings there are
    # silently lost (verified empirically on the pinned semgrep 1.161.0). The ADR
    # permits "guarded to the semgrep versions that support it"; the pin is the
    # guard. This test pins the decision so a future "tidy-up" can't drop it
    # without confronting the coverage regression.
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    rules = tmp_path / "cache" / "semgrep" / "rules"
    rules.mkdir(parents=True)
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))

    captured: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "code_review.adapters.semgrep.run_subprocess", _capture_run(captured)
    )

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(".",),
        languages=frozenset({"python"}),
        config={},
    )
    await SemgrepAdapter().run(request)

    assert captured, "run_subprocess was not called"
    assert "--x-ignore-semgrepignore-files" in captured[0]


async def test_semgrep_override_takes_precedence_over_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    cache_rules = tmp_path / "cache" / "semgrep" / "rules"
    cache_rules.mkdir(parents=True)
    override = tmp_path / "my-rules"
    override.mkdir()
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))

    captured: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "code_review.adapters.semgrep.run_subprocess", _capture_run(captured)
    )

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(".",),
        languages=frozenset({"python"}),
        config={"semgrep_rules": str(override)},
    )
    await SemgrepAdapter().run(request)

    argv = captured[0]
    config_arg = argv[argv.index("--config") + 1]
    assert config_arg == str(override), "override must win over the cache dir"


@pytest.mark.integration
async def test_semgrep_end_to_end_with_provisioned_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """s0-t3: with rules provisioned the way setup.sh does it (vendored ruleset
    copied into cache_root()/cache/semgrep/rules) and NO manual override, the
    adapter returns findings. Proves a clean setup is sufficient (resolves F3)."""
    import importlib.util

    if shutil.which("semgrep") is None:
        pytest.skip("semgrep not on PATH")

    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))

    # Provision exactly as `setup.sh` does — via prefetch_caches.main().
    prefetch_path = Path(__file__).parent.parent.parent / "scripts" / "prefetch_caches.py"
    spec = importlib.util.spec_from_file_location("prefetch_caches", prefetch_path)
    assert spec is not None and spec.loader is not None
    prefetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prefetch)
    assert prefetch.main() == 0
    assert (tmp_path / "cache" / "semgrep" / "rules").is_dir()

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE_PATH),),
        languages=frozenset({"python"}),
        config={},  # no override — rely solely on the provisioned cache
    )
    output = await SemgrepAdapter().run(request)

    assert output.status == "ok", f"expected ok, got {output.status}: {output.error}"
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(output.sarif, schema)
    results = output.sarif.get("runs", [{}])[0].get("results", [])
    assert len(results) >= 1, f"expected >=1 finding from the provisioned cache; got {results}"
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("subprocess-shell-true" in rid for rid in rule_ids), (
        f"expected the vendored subprocess-shell-true rule to fire; got {rule_ids}"
    )


async def test_semgrep_bad_override_fails_loudly_naming_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A typo'd override must not silently fall back to a populated cache.
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    cache_rules = tmp_path / "cache" / "semgrep" / "rules"
    cache_rules.mkdir(parents=True)  # cache IS populated — must still error
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))

    called: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "code_review.adapters.semgrep.run_subprocess", _capture_run(called)
    )

    bad = str(tmp_path / "does-not-exist")
    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(".",),
        languages=frozenset({"python"}),
        config={"semgrep_rules": bad},
    )
    output = await SemgrepAdapter().run(request)

    assert output.status == "error"
    assert output.error is not None and bad in output.error
    assert called == [], "must not run semgrep when the override path is missing"


async def test_semgrep_empty_target_paths_returns_empty_sarif(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    called: list[tuple[object, ...]] = []

    async def _mock_run(*args: object, **kwargs: object) -> object:
        called.append(args)
        return None

    monkeypatch.setattr("code_review.adapters.semgrep.run_subprocess", _mock_run)

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(),
        languages=frozenset(),
        config={},
    )
    output = await SemgrepAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif.get("runs") == []
    assert output.sarif.get("version") == "2.1.0"
    assert "$schema" in output.sarif
    assert called == [], "run_subprocess must not be called for empty target_paths"
