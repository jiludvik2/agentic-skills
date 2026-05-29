from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.contracts import AnalyzerOutput, ReviewRequest
from code_review.paths import trivy_cache_dir as _trivy_cache_dir


class TrivyAdapter:
    name: ClassVar[str] = "trivy"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 180
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "trivy"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        cache_dir = _trivy_cache_dir()
        if not cache_dir.exists():
            return AnalyzerOutput(
                sarif={}, status="error",
                error=(
                    f"Trivy DB not pre-fetched at {cache_dir}. "
                    "Prefetch it with scripts/setup.sh (source checkout), or set "
                    "POLYREVIEW_CACHE_DIR to a directory whose cache/trivy-db is "
                    "already populated."
                ),
            )
        source = request.target_paths[0] if request.target_paths else "."
        with tempfile.TemporaryDirectory(prefix="code-review-trivy-") as _tmp:
            tmp_path = Path(_tmp) / "report.sarif"
            cmd = (
                "trivy", "fs",
                "--format", "sarif",
                "--output", str(tmp_path),
                "--cache-dir", str(cache_dir),
                "--skip-db-update",
                "--offline-scan",
                source,
            )
            result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
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
