from __future__ import annotations

import sys
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest


class BanditAdapter:
    name: ClassVar[str] = "bandit"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if not request.target_paths:
            return CaptureOutput.unavailable("bandit", "no target paths to analyse")
        # --quiet suppresses the info log / progress bar at source (F3); -f json emits the
        # report on stdout. Raw capture — no parsing (ADR-0020). bandit exits 1 when it
        # reports issues, which is success for us → tolerate (0, 1).
        return await run_and_capture(
            "bandit",
            sys.executable, "-m", "bandit",
            "--quiet",
            "--format", "json",
            "-r", *request.target_paths,
            timeout_s=self.default_timeout_s,
            ok_exit_codes=(0, 1),
        )
