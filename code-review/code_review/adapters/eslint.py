from __future__ import annotations

import json
import os
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import node_binary
from code_review.adapters.sarif_utils import empty_sarif, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest
from code_review.paths import node_modules_dir


class EslintAdapter:
    name: ClassVar[str] = "eslint"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 90
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "eslint"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("eslint")
        if binary is None:
            return AnalyzerOutput(
                sarif={}, status="error",
                error="eslint not found. Run scripts/setup.sh first.",
            )
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("eslint"))
        cmd = (
            "node", str(binary),
            "--format", "@microsoft/eslint-formatter-sarif",
            *request.target_paths,
        )
        # The SARIF formatter is a vendored package; eslint resolves it relative
        # to the run cwd, which fails when the target lives outside the skill
        # root. Export NODE_PATH to the vendored node_modules so the formatter
        # resolves regardless of cwd (replaces the smoke harness's stopgap).
        env = dict(os.environ)
        vendored = str(node_modules_dir())
        existing = env.get("NODE_PATH")
        # Prepend the vendored dir so it takes precedence over any inherited path.
        env["NODE_PATH"] = os.pathsep.join([vendored, existing]) if existing else vendored
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s, env=env)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="eslint timed out")
        # ESLint exits 0 (no findings), 1 (findings), 2 (error) — 0 and 1 are success
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"eslint exited {result.returncode}: {stderr}",
            )
        try:
            sarif: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=normalise_sarif(sarif))
