from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest


class CohesionAdapter:
    name: ClassVar[str] = "cohesion"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if not request.target_paths:
            return CaptureOutput.unavailable("cohesion", "no target paths to analyse")
        # cohesion's CLI is `-d <dir>` XOR `-f <files...>` (it errors on `-f <dir>`). A
        # single directory target → -d; otherwise treat the targets as a file list → -f.
        # (Mixed file+dir targets fall to -f and surface cohesion's own error as a non-ok
        # status — a rare shape for this Python-scoped tool.) Invoked via `python -m
        # cohesion` (pinned dep, always present like bandit/pydeps — no PATH-binary gating).
        # Raw capture, no parsing (ADR-0020); cohesion writes its per-class report to
        # stdout, exit 0.
        paths = request.target_paths
        tool_args: tuple[str, ...]
        if len(paths) == 1 and Path(paths[0]).is_dir():
            tool_args = ("-d", paths[0])
        else:
            tool_args = ("-f", *paths)
        return await run_and_capture(
            "cohesion",
            sys.executable, "-m", "cohesion", *tool_args,
            timeout_s=self.default_timeout_s,
        )
