from __future__ import annotations

import sys
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest


class RadonAdapter:
    name: ClassVar[str] = "radon"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if not request.target_paths:
            return CaptureOutput.unavailable("radon", "no target paths to analyse")
        # `cc --json` emits per-file cyclomatic complexity as JSON on stdout — the
        # load-bearing scan default. Invoked via `python -m radon` (radon is a pinned dep,
        # always present like bandit/pydeps — no PATH-binary gating, stays capability-
        # available). Raw capture, no parsing (ADR-0020); radon exits 0 on success.
        return await run_and_capture(
            "radon",
            sys.executable, "-m", "radon", "cc", "--json", *request.target_paths,
            timeout_s=self.default_timeout_s,
        )
