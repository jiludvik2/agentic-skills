from __future__ import annotations

import sys
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest


class PydepsAdapter:
    name: ClassVar[str] = "pydeps"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if not request.target_paths:
            return CaptureOutput.unavailable("pydeps", "no target paths to analyse")
        target = request.target_paths[0]
        # --show-deps emits the dependency map as JSON on stdout; --no-output/--noshow
        # suppress the .svg/.png graph render. Raw capture — no parsing here (ADR-0020).
        return await run_and_capture(
            "pydeps",
            sys.executable, "-m", "pydeps", target,
            "--show-deps", "--no-output", "--noshow",
            timeout_s=self.default_timeout_s,
        )
