from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import has_js_files, js_unavailable, node_binary
from code_review.adapters.sarif_utils import empty_sarif, make_location, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for dup in data.get("duplicates", []):
        first = dup.get("firstFile", {})
        second = dup.get("secondFile", {})
        results.append(
            {
                "ruleId": "jscpd.duplicate-code",
                "message": {
                    "text": (
                        f"Duplicate code block: {first.get('name', '?')} "
                        f"and {second.get('name', '?')}"
                    )
                },
                "locations": [
                    make_location(first.get("name", "unknown"), first.get("start", 1))
                ],
                "relatedLocations": [
                    {
                        "id": 1,
                        "message": {"text": "Duplicate location"},
                        "physicalLocation": {
                            "artifactLocation": {"uri": second.get("name", "unknown")},
                            "region": {"startLine": second.get("start", 1)},
                        },
                    }
                ],
            }
        )
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {"driver": {"name": "jscpd", "version": "4.0.5", "rules": []}},
                    "results": results,
                }
            ]
        }
    )


class JscpdAdapter:
    name: ClassVar[str] = "jscpd"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "jscpd"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("jscpd")
        if binary is None:
            return AnalyzerOutput(
                sarif={}, status="error",
                error="jscpd not found. Run scripts/setup.sh first.",
            )
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("jscpd"))
        # jscpd is intentionally JS-scoped in polyreview (lang_select._JS_ADAPTERS;
        # capabilities languages=[javascript, typescript]) — duplication detection is
        # a deliberately JS-only feature. Skip cleanly on a no-JS target rather than
        # run the out-of-scope language duplication jscpd is capable of (ADR-0019).
        # Defense-in-depth for the all-analyzer / --target path that bypasses the
        # selector's language filter; mirrors eslint/knip.
        if not has_js_files(request.target_paths):
            return js_unavailable("jscpd", "no JavaScript/TypeScript files in target")
        # jscpd treats --output as a *directory* it mkdir's and writes
        # jscpd-report.json into; pointing it at /dev/stdout fails with EEXIST.
        # Use a TemporaryDirectory and read the report, like trivy/gitleaks.
        with tempfile.TemporaryDirectory(prefix="code-review-jscpd-") as _tmp:
            report = Path(_tmp) / "jscpd-report.json"
            cmd = (
                "node", str(binary),
                "--reporters", "json",
                "--output", _tmp,
                *request.target_paths,
            )
            result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
            if result.error is not None:
                return AnalyzerOutput(sarif={}, status="error", error=result.error)
            if result.timed_out:
                return AnalyzerOutput(sarif={}, status="timeout", error="jscpd timed out")
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")
                return AnalyzerOutput(
                    sarif={}, status="error",
                    error=f"jscpd exited {result.returncode}: {stderr}",
                )
            if not report.exists():
                return AnalyzerOutput(sarif={}, status="error",
                                      error="jscpd produced no report file")
            try:
                data: dict[str, Any] = json.loads(report.read_text())
            except json.JSONDecodeError as exc:
                return AnalyzerOutput(sarif={}, status="error",
                                      error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
