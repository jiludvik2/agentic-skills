from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.contracts import AnalyzerOutput, ReviewRequest


class GitleaksAdapter:
    name: ClassVar[str] = "gitleaks"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "gitleaks"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        source = request.target_paths[0] if request.target_paths else "."
        tmp_path = Path.cwd() / f".gitleaks-{uuid.uuid4().hex}.sarif"
        cmd = (
            "gitleaks", "detect",
            "--source", source,
            "--report-format", "sarif",
            "--report-path", str(tmp_path),
            "--no-git",
            "--exit-code", "0",
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        try:
            if result.error is not None:
                return AnalyzerOutput(sarif={}, status="error", error=result.error)
            if result.timed_out:
                return AnalyzerOutput(sarif={}, status="timeout", error="gitleaks timed out")
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")
                return AnalyzerOutput(
                    sarif={}, status="error",
                    error=f"gitleaks exited {result.returncode}: {stderr}",
                )
            if not tmp_path.exists():
                return AnalyzerOutput(sarif={}, status="error",
                                      error="gitleaks produced no report file")
            sarif: dict[str, Any] = json.loads(tmp_path.read_text())
            return AnalyzerOutput(sarif=sarif)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
