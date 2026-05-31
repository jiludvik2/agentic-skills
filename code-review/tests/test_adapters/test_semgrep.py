"""s1-t1 — semgrep invoke-and-capture contract (ADR-0020 / ADR-0016).

Pins the load-bearing invocation (--sarif, --config <rules>, --metrics off, and the
load-bearing --x-ignore-semgrepignore-files), the rules-resolution order, the raw
passthrough, and the availability pre-flights (missing binary / missing provisioned
rules / bad override → unavailable per ADR-0019; semgrep is never run in those cases).
"""

import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.semgrep import SemgrepAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
JS_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "js-with-security-issues"
RULES_PATH = Path(__file__).parent.parent / "fixtures" / "semgrep-rules"


def _req(paths: tuple[str, ...], config: dict | None = None) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset({"python"}), config=config or {})


def _present() -> object:
    """Patch ctx: semgrep binary present on PATH (so the which pre-flight passes)."""
    return patch("code_review.adapters.semgrep.shutil.which", return_value="/usr/bin/semgrep")


def _provision_vendored_rules() -> None:
    """Provision the vendored ruleset the way setup.sh does, into the cache root the
    caller has already pointed POLYREVIEW_CACHE_DIR at. Asserts a clean exit."""
    import importlib.util

    prefetch_path = Path(__file__).parent.parent.parent / "scripts" / "prefetch_caches.py"
    spec = importlib.util.spec_from_file_location("prefetch_caches", prefetch_path)
    assert spec is not None and spec.loader is not None
    prefetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prefetch)
    assert prefetch.main() == 0


def test_semgrep_protocol_conformance() -> None:
    assert isinstance(SemgrepAdapter(), Analyzer)
    assert SemgrepAdapter.name == "semgrep"
    assert SemgrepAdapter.required_binary == "semgrep"


async def test_semgrep_invocation_pins_flags(tmp_path: Path) -> None:
    rules = tmp_path / "rules"
    rules.mkdir()
    mock = AsyncMock(return_value=CaptureOutput(tool="semgrep"))
    with _present(), patch("code_review.adapters.semgrep.run_and_capture", new=mock):
        await SemgrepAdapter().run(_req((str(FIXTURE_PATH),), {"semgrep_rules": str(rules)}))
    args = mock.call_args.args
    assert args[0] == "semgrep"
    assert "--sarif" in args
    assert "--metrics" in args and args[args.index("--metrics") + 1] == "off"
    assert args[args.index("--config") + 1] == str(rules)
    assert "--x-ignore-semgrepignore-files" in args  # load-bearing (ADR-0016)
    assert str(FIXTURE_PATH) in args
    # findings present ⇒ exit 1 must be tolerated as success
    assert mock.call_args.kwargs["ok_exit_codes"] == (0, 1)
    assert "env" in mock.call_args.kwargs  # settings/log redirect env is threaded


async def test_semgrep_captures_raw_stdout(tmp_path: Path) -> None:
    rules = tmp_path / "rules"
    rules.mkdir()
    cap = CaptureOutput(tool="semgrep", stdout='{"runs": [{"results": []}]}', exit_code=0)
    with _present(), patch("code_review.adapters.semgrep.run_and_capture",
                           new=AsyncMock(return_value=cap)):
        out = await SemgrepAdapter().run(_req(("x.py",), {"semgrep_rules": str(rules)}))
    assert out is cap
    assert out.stdout == '{"runs": [{"results": []}]}'


async def test_semgrep_rules_dir_honors_cache_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rules = tmp_path / "cache" / "semgrep" / "rules"
    rules.mkdir(parents=True)
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    mock = AsyncMock(return_value=CaptureOutput(tool="semgrep"))
    with _present(), patch("code_review.adapters.semgrep.run_and_capture", new=mock):
        await SemgrepAdapter().run(_req((".",)))
    args = mock.call_args.args
    assert args[args.index("--config") + 1] == str(rules)


async def test_semgrep_override_takes_precedence_over_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "cache" / "semgrep" / "rules").mkdir(parents=True)
    override = tmp_path / "my-rules"
    override.mkdir()
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    mock = AsyncMock(return_value=CaptureOutput(tool="semgrep"))
    with _present(), patch("code_review.adapters.semgrep.run_and_capture", new=mock):
        await SemgrepAdapter().run(_req((".",), {"semgrep_rules": str(override)}))
    args = mock.call_args.args
    assert args[args.index("--config") + 1] == str(override)


async def test_semgrep_unavailable_when_binary_absent() -> None:
    with patch("code_review.adapters.semgrep.shutil.which", return_value=None):
        out = await SemgrepAdapter().run(_req((".",)))
    assert out.status == "unavailable"


async def test_semgrep_unavailable_on_empty_targets() -> None:
    out = await SemgrepAdapter().run(_req(()))
    assert out.status == "unavailable"


async def test_semgrep_unavailable_when_cache_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Empty cache root: no provisioned rules, no override → unavailable (not error),
    # and semgrep must never be invoked.
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    mock = AsyncMock(return_value=CaptureOutput(tool="semgrep"))
    with _present(), patch("code_review.adapters.semgrep.run_and_capture", new=mock):
        out = await SemgrepAdapter().run(_req((".",)))
    assert out.status == "unavailable"
    assert "setup.sh" in (out.error or "")
    assert mock.await_count == 0


async def test_semgrep_bad_override_fails_loudly_naming_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A typo'd override must not silently fall back to a populated cache, and must not run.
    (tmp_path / "cache" / "semgrep" / "rules").mkdir(parents=True)
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    bad = str(tmp_path / "does-not-exist")
    mock = AsyncMock(return_value=CaptureOutput(tool="semgrep"))
    with _present(), patch("code_review.adapters.semgrep.run_and_capture", new=mock):
        out = await SemgrepAdapter().run(_req((".",), {"semgrep_rules": bad}))
    assert out.status == "unavailable"
    assert bad in (out.error or "")
    assert mock.await_count == 0


async def test_base_subprocess_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    # Guards the base primitive's timeout classification (unchanged by the migration).
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


@pytest.mark.integration
async def test_semgrep_end_to_end_with_provisioned_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With rules provisioned the way setup.sh does it (vendored ruleset copied into
    cache_root()/cache/semgrep/rules) and NO override, the raw capture carries the
    vendored rule's finding (resolves F3; analyzer-coverage discipline)."""
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep not on PATH")

    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    _provision_vendored_rules()
    assert (tmp_path / "cache" / "semgrep" / "rules").is_dir()

    out = await SemgrepAdapter().run(_req((str(FIXTURE_PATH),)))
    assert out.status == "ok", f"expected ok, got {out.status}: {out.error}"
    payload = json.loads(out.stdout)  # raw SARIF text on stdout
    results = payload.get("runs", [{}])[0].get("results", [])
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("subprocess-shell-true" in rid for rid in rule_ids), (
        f"expected the vendored subprocess-shell-true rule to fire; got {rule_ids}"
    )


@pytest.mark.integration
async def test_semgrep_js_rules_fire_on_js_fixture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Vendored JS rules fire on a planted JS fixture end-to-end (s3 / G6).

    Architecture validation (ADR-0020): adding JS coverage required only a new
    vendored rule file — the provisioning path globs ``*.y*ml`` so it is auto-copied,
    and no adapter code changed.
    """
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep not on PATH")

    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    _provision_vendored_rules()
    assert (tmp_path / "cache" / "semgrep" / "rules" / "security-js.yaml").exists()

    out = await SemgrepAdapter().run(_req((str(JS_FIXTURE_PATH),)))
    assert out.status == "ok", f"expected ok, got {out.status}: {out.error}"
    payload = json.loads(out.stdout)
    rule_ids = [r.get("ruleId", "") for r in payload.get("runs", [{}])[0].get("results", [])]
    assert any("js-eval" in rid for rid in rule_ids), f"js-eval not fired; got {rule_ids}"
    assert any(
        "js-innerhtml-xss" in rid for rid in rule_ids
    ), f"js-innerhtml-xss not fired; got {rule_ids}"
