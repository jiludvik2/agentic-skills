import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import jsonschema
import pytest

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"


def test_semgrep_protocol_conformance():
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import Analyzer

    adapter = SemgrepAdapter()
    assert isinstance(adapter, Analyzer)
    assert SemgrepAdapter.name == "semgrep"


@pytest.mark.integration
async def test_semgrep_produces_valid_sarif():
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep not on PATH")

    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE_PATH),),
        languages=frozenset({"python"}),
        config={},
    )
    output = await SemgrepAdapter().run(request)

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(output.sarif, schema)

    results = output.sarif.get("runs", [{}])[0].get("results", [])
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("subprocess-shell-true" in rid for rid in rule_ids), (
        f"Expected subprocess-shell-true finding; got rule IDs: {rule_ids}"
    )


async def test_semgrep_missing_binary_returns_error(monkeypatch: pytest.MonkeyPatch):
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


async def test_base_subprocess_timeout(monkeypatch: pytest.MonkeyPatch):
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


async def test_semgrep_empty_target_paths_returns_empty_sarif(monkeypatch: pytest.MonkeyPatch) -> None:
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
