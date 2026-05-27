from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.contracts import AnalyzerOutput, ReviewRequest

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "skills" / "code-review"
_TRIVY_CACHE_DIR = _SKILL_DIR / "cache" / "trivy-db"


class TrivyAdapter:
    name: ClassVar[str] = "trivy"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 180
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "trivy"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not _TRIVY_CACHE_DIR.exists():
            return AnalyzerOutput(
                sarif={}, status="error",
                error=(
                    f"Trivy DB not pre-fetched. Run scripts/setup.sh."
                    f" Expected: {_TRIVY_CACHE_DIR}"
                ),
            )
        source = request.target_paths[0] if request.target_paths else "."
        tmp_path = Path.cwd() / f".trivy-{uuid.uuid4().hex}.sarif"
        cmd = (
            "trivy", "fs",
            "--format", "sarif",
            "--output", str(tmp_path),
            "--cache-dir", str(_TRIVY_CACHE_DIR),
            "--skip-db-update",
            "--offline-scan",
            source,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        try:
            if result.error is not None:
                return AnalyzerOutput(sarif={}, status="error", error=result.error)
            if result.timed_out:
                return AnalyzerOutput(sarif={}, status="timeout", error="trivy timed out")
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")
                return AnalyzerOutput(
                    sarif={}, status="error",
                    error=f"trivy exited {result.returncode}: {stderr}",
                )
            if not tmp_path.exists():
                return AnalyzerOutput(sarif={}, status="error",
                                      error="trivy produced no output file")
            sarif: dict[str, Any] = json.loads(tmp_path.read_text())
            return AnalyzerOutput(sarif=sarif)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
