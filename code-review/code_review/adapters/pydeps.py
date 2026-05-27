from __future__ import annotations

import json
import sys
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.sarif_utils import empty_sarif, normalise_sarif
from code_review.contracts import AnalyzerOutput, MetricSet, ReviewRequest

_HIGH_FAN_OUT_THRESHOLD = 10


def _to_sarif_and_metrics(deps: dict[str, Any]) -> tuple[dict[str, Any], MetricSet]:
    fan_in: dict[str, int] = {k: 0 for k in deps}
    for entry in deps.values():
        for imp in entry.get("imports", []):
            if imp in fan_in:
                fan_in[imp] += 1

    coupling: dict[str, dict[str, Any]] = {}
    results = []
    for mod_name, entry in deps.items():
        imports: list[str] = entry.get("imports", [])
        fo = len(imports)
        fi = fan_in.get(mod_name, 0)
        coupling[mod_name] = {"fan_out": fo, "fan_in": fi, "imports": imports}
        if fo >= _HIGH_FAN_OUT_THRESHOLD:
            results.append(
                {
                    "ruleId": "pydeps.high-fan-out",
                    "message": {
                        "text": (
                            f"module '{mod_name}' has fan-out {fo}"
                            f" (threshold {_HIGH_FAN_OUT_THRESHOLD})"
                        )
                    },
                    "locations": [],
                }
            )

    sarif = normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "pydeps", "version": "1.12.20", "rules": []}
                    },
                    "results": results,
                }
            ]
        }
    )
    return sarif, MetricSet(per_file={}, per_class={}, coupling=coupling)


class PydepsAdapter:
    name: ClassVar[str] = "pydeps"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(
                sarif=empty_sarif("pydeps", "1.12.20"),
                metrics=MetricSet(per_file={}, per_class={}, coupling={}),
            )
        target = request.target_paths[0]
        cmd = (
            sys.executable,
            "-m",
            "pydeps",
            target,
            "--show-deps",
            "--no-output",
            "--noshow",
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="pydeps timed out")
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={},
                status="error",
                error=f"pydeps exited {result.returncode}: {stderr}",
            )
        try:
            deps: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        sarif, metrics = _to_sarif_and_metrics(deps)
        return AnalyzerOutput(sarif=sarif, metrics=metrics)
