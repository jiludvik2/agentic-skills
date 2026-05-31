from __future__ import annotations

import sys
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest


class VultureAdapter:
    name: ClassVar[str] = "vulture"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if not request.target_paths:
            return CaptureOutput.unavailable("vulture", "no target paths to analyse")
        # vulture writes its dead-code report (`file:line: unused …`) to stdout. Invoked via
        # `python -m vulture` (pinned dep, always present like bandit/pydeps — no PATH-binary
        # gating). Raw capture, no parsing (ADR-0020). It exits 3 (ExitCode.DeadCode) when it
        # finds dead code and 0 when clean — both are success → tolerate (0, 3). Exit 1/2 are
        # real errors (InvalidInput / InvalidCmdlineArguments) and stay non-ok.
        return await run_and_capture(
            "vulture",
            sys.executable, "-m", "vulture", *request.target_paths,
            timeout_s=self.default_timeout_s,
            ok_exit_codes=(0, 3),
        )
