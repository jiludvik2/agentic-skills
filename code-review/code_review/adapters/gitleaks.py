from __future__ import annotations

import shutil
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest


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
        # Capture gitleaks' native finding output (no --report-path: a /dev/stdout redirect
        # is unreliable under sandboxed/containerised environments, and a temp file would
        # reintroduce the parse-from-file the thin runner deletes). The bundle carries both
        # stdout and stderr, so the agent reads whichever stream gitleaks reports findings on
        # (ADR-0020). gitleaks exits 1 when leaks are present → tolerate (0, 1). --no-git
        # scans the working tree, not history.
        return await run_and_capture(
            "gitleaks",
            "gitleaks", "detect",
            "--source", source,
            "--no-git",
            timeout_s=self.default_timeout_s,
            ok_exit_codes=(0, 1),
        )
