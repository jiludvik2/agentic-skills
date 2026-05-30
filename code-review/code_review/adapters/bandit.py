from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.sarif_utils import (
    make_location,
    normalise_sarif,
    rel_uri,
)
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    cwd = str(Path.cwd())
    results = []
    for r in data.get("results", []):
        cwe_id = r.get("issue_cwe", {}).get("id")
        taxa = (
            [{"toolComponent": {"name": "cwe"}, "id": str(cwe_id)}] if cwe_id else []
        )
        results.append(
            {
                "ruleId": f"bandit.{r['test_id']}",
                "message": {"text": r["issue_text"]},
                "locations": [make_location(rel_uri(r["filename"], cwd), r["line_number"])],
                "taxa": taxa,
            }
        )
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "bandit", "version": "1.7.10", "rules": []}
                    },
                    "results": results,
                }
            ]
        }
    )


class BanditAdapter:
    name: ClassVar[str] = "bandit"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(sarif=normalise_sarif({"runs": []}))
        cmd = (
            sys.executable, "-m", "bandit",
            "--quiet",  # suppress the info log / progress bar at source (F3)
            "--format", "json",
            "-r", *request.target_paths,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="bandit timed out")
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"bandit exited {result.returncode}: {stderr}",
            )
        # Defensive: tolerate a Rich progress-bar prefix on stdout should --quiet not
        # suppress it. The first '{' is the JSON start (the bar contains no braces);
        # if there is none we fail loudly below rather than corrupt the parse (F3).
        stdout = result.stdout
        raw = stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout
        brace = raw.find("{")
        if brace == -1:
            return AnalyzerOutput(
                sarif={}, status="error", error="invalid JSON: no JSON object in bandit output"
            )
        try:
            data: dict[str, Any] = json.loads(raw[brace:])
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
