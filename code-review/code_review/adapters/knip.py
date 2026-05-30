from __future__ import annotations

import json
import os
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import js_unavailable, node_binary
from code_review.adapters.sarif_utils import empty_sarif, make_location, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for filepath in data.get("files", []):
        results.append(
            {
                "ruleId": "knip.unused-file",
                "message": {"text": f"Unused file: {filepath}"},
                "locations": [make_location(filepath, 1)],
            }
        )
    for export in data.get("exports", []):
        results.append(
            {
                "ruleId": "knip.unused-export",
                "message": {
                    "text": (
                        f"Unused export '{export.get('symbol', '?')}' "
                        f"in {export.get('file', '?')}"
                    )
                },
                "locations": [make_location(export.get("file", "unknown"), 1)],
            }
        )
    # data["dependencies"] (unused npm deps) intentionally not mapped to findings
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {"driver": {"name": "knip", "version": "5.0.0", "rules": []}},
                    "results": results,
                }
            ]
        }
    )


class KnipAdapter:
    name: ClassVar[str] = "knip"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "knip"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("knip")
        if binary is None:
            return AnalyzerOutput(
                sarif={}, status="error",
                error="knip not found. Run scripts/setup.sh first.",
            )
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("knip"))
        # knip is a whole-project tool: it reads ./package.json from its cwd. With
        # none present (e.g. a pure-Python review) it errors "Unable to find
        # package.json" — report that as a clean skip, not a failure (ADR-0019).
        target = request.target_paths[0]
        project_dir = target if os.path.isdir(target) else os.path.dirname(target)
        if not os.path.isfile(os.path.join(project_dir, "package.json")):
            return js_unavailable("knip", f"no package.json under {project_dir}")
        cmd = ("node", str(binary), "--reporter", "json")
        result = await run_subprocess(
            *cmd, timeout_s=self.default_timeout_s, cwd=project_dir
        )
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="knip timed out")
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"knip exited {result.returncode}: {stderr}",
            )
        try:
            data: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
