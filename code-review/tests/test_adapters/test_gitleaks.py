"""s2-t0 — gitleaks invoke-and-capture contract (ADR-0020).

Supersedes the s1-t1 no-report-path decision: gitleaks prints only a "leaks found: N"
banner to stderr and nothing to stdout, so under raw-capture the findings were lost
(a silent false-negative in a security analyzer). The adapter now writes a JSON report
to an off-argv temp file and splices it onto the capture's stdout (the trivy/jscpd
pattern) — NOT a /dev/stdout redirect (unwritable under the OS sandbox). These tests
pin the off-argv report path, the read-back, the sandbox-safe temp file, and the
missing-binary availability pre-flight.
"""

import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.gitleaks import GitleaksAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

# A Slack bot token is reliably flagged by gitleaks' default rules (the AWS "…EXAMPLE"
# dummy is allowlisted, so it would NOT detect — a vacuous fixture). All dummy values.
_SLACK_TOKEN = "xoxb-0000000000-0000000000000-abcdefghijklmnopqrstuvwx"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


@contextmanager
def _gitleaks_env(run_mock: AsyncMock) -> Iterator[None]:
    """Patch the binary lookup (present) and run_and_capture with ``run_mock``."""
    with patch("code_review.adapters.gitleaks.shutil.which", return_value="/x"), \
         patch("code_review.adapters.gitleaks.run_and_capture", new=run_mock):
        yield


def test_gitleaks_protocol_conformance() -> None:
    assert isinstance(GitleaksAdapter(), Analyzer)
    assert GitleaksAdapter.name == "gitleaks"
    assert GitleaksAdapter.required_binary == "gitleaks"


async def test_gitleaks_invocation_uses_offargv_json_report() -> None:
    """The adapter must invoke gitleaks with `--report-format json --report-path <tmp>`
    where the path is a real temp file (sandbox-safe), never a /dev/stdout redirect.
    RED before s2-t0: the adapter passed no report path at all."""
    seen: dict[str, object] = {}

    async def fake_run(tool: str, *cmd: str, **kwargs: object) -> CaptureOutput:
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        rp = cmd[cmd.index("--report-path") + 1]
        Path(rp).write_text("[]")  # gitleaks always writes the report (clean → [])
        return CaptureOutput(tool="gitleaks", stdout="", stderr="", exit_code=0)

    with _gitleaks_env(AsyncMock(side_effect=fake_run)):
        await GitleaksAdapter().run(_req((".",)))
    cmd = seen["cmd"]
    assert isinstance(cmd, tuple)
    assert cmd[0] == "gitleaks" and "detect" in cmd and "--no-git" in cmd
    assert cmd[cmd.index("--report-format") + 1] == "json"
    report_path = cmd[cmd.index("--report-path") + 1]
    assert "/dev/stdout" not in report_path, "must be a real temp file, not a /dev/stdout redirect"
    assert Path(report_path).name.endswith(".json")
    # leaks-present exit 1 must still be tolerated as success.
    assert seen["kwargs"]["ok_exit_codes"] == (0, 1)  # type: ignore[index]


async def test_gitleaks_splices_report_onto_stdout() -> None:
    """The JSON report written off-argv is read back onto the capture's stdout, so the
    bundle carries machine-readable findings. RED before s2-t0: stdout stayed empty
    (findings only in the stderr banner)."""
    report_json = '[{"RuleID": "slack-bot-token", "File": "leak.py", "StartLine": 1}]'

    async def fake_run(tool: str, *cmd: str, **kwargs: object) -> CaptureOutput:
        Path(cmd[cmd.index("--report-path") + 1]).write_text(report_json)
        # gitleaks reports the leak count to stderr and nothing to stdout.
        return CaptureOutput(tool="gitleaks", stdout="", stderr="leaks found: 1", exit_code=1)

    with _gitleaks_env(AsyncMock(side_effect=fake_run)):
        out = await GitleaksAdapter().run(_req((".",)))
    assert out.status == "ok", out.error
    assert out.stdout == report_json, "the off-argv report must be spliced onto stdout"
    assert json.loads(out.stdout)[0]["RuleID"] == "slack-bot-token"


async def test_gitleaks_clean_scan_yields_empty_array() -> None:
    """A clean scan (exit 0) writes `[]` to the report; that empty array is captured on
    stdout (downstream reads 'ran, found nothing'), not flipped to error."""
    async def fake_run(tool: str, *cmd: str, **kwargs: object) -> CaptureOutput:
        Path(cmd[cmd.index("--report-path") + 1]).write_text("[]")
        return CaptureOutput(tool="gitleaks", stdout="", exit_code=0)

    with _gitleaks_env(AsyncMock(side_effect=fake_run)):
        out = await GitleaksAdapter().run(_req((".",)))
    assert out.status == "ok", out.error
    assert out.stdout == "[]"


async def test_gitleaks_missing_report_on_ok_is_error() -> None:
    """If gitleaks exits OK but no report file landed (anomaly), an empty stdout would
    read downstream as 'found nothing' and mask the failure — flip it to error instead."""
    async def fake_run(tool: str, *cmd: str, **kwargs: object) -> CaptureOutput:
        # Deliberately do NOT write the report file.
        return CaptureOutput(tool="gitleaks", stdout="", exit_code=0)

    with _gitleaks_env(AsyncMock(side_effect=fake_run)):
        out = await GitleaksAdapter().run(_req((".",)))
    assert out.status == "error"
    assert "report" in (out.error or "").lower()


async def test_gitleaks_passthrough_on_failed_run() -> None:
    """A genuinely failed gitleaks run (non-ok status) is passed through verbatim — no
    read-back attempted on a run that wrote no usable report."""
    from code_review.status import Status
    failed = CaptureOutput(tool="gitleaks", status=Status.ERROR, stderr="boom", exit_code=2,
                           error="exited 2: boom")
    with _gitleaks_env(AsyncMock(return_value=failed)):
        out = await GitleaksAdapter().run(_req((".",)))
    assert out is failed


async def test_gitleaks_unavailable_when_binary_absent() -> None:
    with patch("code_review.adapters.gitleaks.shutil.which", return_value=None):
        out = await GitleaksAdapter().run(_req((".",)))
    assert out.status == "unavailable"
    assert out.error is not None


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
async def test_gitleaks_integration_detects_secret(tmp_path: Path) -> None:
    """Real gitleaks against a planted Slack token: the finding must be parseable from
    captured stdout JSON (≥1 finding with a rule id), not merely echoed in the stderr
    banner. This is the regression guard against the silent-false-negative class."""
    (tmp_path / "leak.py").write_text(f'SLACK_TOKEN = "{_SLACK_TOKEN}"\n')
    out = await GitleaksAdapter().run(_req((str(tmp_path),)))
    assert out.status == "ok", out.error
    findings = json.loads(out.stdout)
    assert isinstance(findings, list) and findings, f"expected ≥1 finding, got {out.stdout!r}"
    assert any("RuleID" in f for f in findings), findings


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
async def test_gitleaks_integration_clean_tree_empty_array(tmp_path: Path) -> None:
    """Real gitleaks on a clean tree: exit 0, stdout carries the empty JSON array `[]`."""
    (tmp_path / "ok.py").write_text("x = 1\n")
    out = await GitleaksAdapter().run(_req((str(tmp_path),)))
    assert out.status == "ok", out.error
    assert json.loads(out.stdout) == []
