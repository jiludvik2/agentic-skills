from __future__ import annotations

import shutil
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest
from code_review.paths import trivy_cache_dir as _trivy_cache_dir


class TrivyAdapter:
    name: ClassVar[str] = "trivy"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 180
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "trivy"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if shutil.which(self.required_binary) is None:
            return CaptureOutput.unavailable("trivy", "trivy not found on PATH")
        cache_dir = _trivy_cache_dir()
        if not cache_dir.exists():
            # Provisioning gap → unavailable (ADR-0019: not runnable here), not error.
            return CaptureOutput.unavailable(
                "trivy",
                f"Trivy DB not pre-fetched at {cache_dir}. Prefetch it with "
                "scripts/setup.sh (source checkout), or set POLYREVIEW_CACHE_DIR to a "
                "directory whose cache/trivy-db is already populated.",
            )
        source = request.target_paths[0] if request.target_paths else "."
        # No --output: trivy writes the SARIF report to stdout natively (a /dev/stdout
        # redirect is unreliable under sandboxed/containerised environments). Logs go to
        # stderr. --skip-db-update + --offline-scan keep it offline (provisioned DB, no
        # egress). Raw capture — no parsing (ADR-0020).
        return await run_and_capture(
            "trivy",
            "trivy", "fs",
            "--format", "sarif",
            "--cache-dir", str(cache_dir),
            "--skip-db-update",
            "--offline-scan",
            source,
            timeout_s=self.default_timeout_s,
        )
