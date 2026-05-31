from __future__ import annotations

import os
from typing import ClassVar

from code_review.adapters.js_base import node_binary
from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest


class KnipAdapter:
    name: ClassVar[str] = "knip"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "knip"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        binary = node_binary("knip")
        if binary is None:
            # Missing vendored binary → provisioning gap, not a scan failure (ADR-0019).
            return CaptureOutput.unavailable(
                "knip", "knip not found in vendored node_modules. Run scripts/setup.sh first."
            )
        if not request.target_paths:
            return CaptureOutput.unavailable("knip", "no target paths to analyse")
        # knip is a whole-project tool: it reads ./package.json from its cwd. With none
        # present (e.g. a pure-Python review) it errors "Unable to find package.json" —
        # report that as a clean skip, not a failure (ADR-0019).
        target = request.target_paths[0]
        project_dir = target if os.path.isdir(target) else os.path.dirname(target)
        if not os.path.isfile(os.path.join(project_dir, "package.json")):
            return CaptureOutput.unavailable("knip", f"no package.json under {project_dir}")
        # --reporter json puts the unused-file/-export findings on stdout, captured verbatim
        # (ADR-0020 — no parse here). knip exits 0 (clean) or 1 (findings) — both success.
        cmd = ("node", str(binary), "--reporter", "json")
        return await run_and_capture(
            "knip", *cmd,
            timeout_s=self.default_timeout_s,
            cwd=project_dir,
            ok_exit_codes=(0, 1),
        )
