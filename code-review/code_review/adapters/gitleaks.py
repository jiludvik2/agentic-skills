from __future__ import annotations

import dataclasses
import shutil
import tempfile
from pathlib import Path
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest
from code_review.status import Status


class GitleaksAdapter:
    name: ClassVar[str] = "gitleaks"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "gitleaks"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if shutil.which(self.required_binary) is None:
            return CaptureOutput.unavailable("gitleaks", "gitleaks not found on PATH")
        source = request.target_paths[0] if request.target_paths else "."
        # gitleaks prints ONLY a "leaks found: N" banner to stderr and nothing to stdout
        # (confirmed empirically: 10 real leaks on pygoat, captured stdout 0 B). Under
        # raw-capture (ADR-0020) that reads downstream as "no secrets" — a silent
        # false-negative in a security analyzer. So write the JSON report to an off-argv
        # temp file and splice it onto the capture's stdout (the trivy/jscpd pattern). NOT
        # a /dev/stdout redirect: unwritable under the OS sandbox (memory
        # dev-stdout-not-writable; FINDINGS F2). This supersedes the s1-t1 no-report-path
        # decision — that left findings uncaptured. gitleaks exits 1 when leaks are present
        # → tolerate (0, 1); --no-git scans the working tree, not git history.
        with tempfile.TemporaryDirectory(prefix="code-review-gitleaks-") as tmp:
            report = Path(tmp) / "gitleaks-report.json"
            cmd = (
                "gitleaks", "detect",
                "--source", source,
                "--no-git",
                "--report-format", "json",
                "--report-path", str(report),
            )
            capture = await run_and_capture(
                "gitleaks", *cmd, timeout_s=self.default_timeout_s, ok_exit_codes=(0, 1)
            )
            if capture.status is not Status.OK:
                # Failed/timed-out run wrote no usable report — pass the raw capture through.
                return capture
            if not report.exists():
                # Exited ok but produced no report (anomaly). An empty stdout would read
                # downstream as "ran, found nothing" and mask the silence — flip to error
                # (mirrors the jscpd missing-report guard).
                return dataclasses.replace(
                    capture, status=Status.ERROR, error="gitleaks produced no report file"
                )
            return dataclasses.replace(capture, stdout=report.read_text(errors="replace"))
