from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import node_binary
from code_review.adapters.sarif_utils import empty_sarif, make_location, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest

# dependency-cruiser refuses to run without a config (it aborts with "Can't open
# a config file"), so the adapter supplies its own rather than requiring the host
# target to ship a .dependency-cruiser.cjs (s3-t1). Two deliberate choices:
#   - enhancedResolveOptions.extensions (NOT tsConfig): lets depcruise resolve
#     bare ./foo TS/JS imports so circular edges are seen, without hard-requiring
#     a tsconfig.json that arbitrary targets won't have.
#   - no `forbidden` rules: the adapter reads each dependency's `circular` flag
#     from the JSON output directly; a forbidden rule would make depcruise exit
#     non-zero on a violation, which this adapter treats as an error.
_CRUISE_CONFIG = """\
module.exports = {
  options: {
    doNotFollow: { path: "node_modules" },  // skip vendored deps
    enhancedResolveOptions: {
      extensions: [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json"],
    },
  },
};
"""


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for module in data.get("modules", []):
        source = module.get("source", "unknown")
        for dep in module.get("dependencies", []):
            if dep.get("circular", False):
                results.append(
                    {
                        "ruleId": "depcruiser.circular-dependency",
                        "message": {
                            "text": (
                                f"Circular dependency: {source} "
                                f"→ {dep.get('resolved', '?')}"
                            )
                        },
                        "locations": [make_location(source, 1)],
                    }
                )
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "dependency-cruiser",
                            # Keep in sync with the dependency-cruiser pin in
                            # capabilities.json / package-lock.json (no drift
                            # guard reaches this SARIF literal — see s3-t0 notes).
                            "version": "16.10.4",
                            "rules": [],
                        }
                    },
                    "results": results,
                }
            ]
        }
    )


class DependencyCruiserAdapter:
    name: ClassVar[str] = "depcruiser"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 90
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "depcruise"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("depcruise")
        if binary is None:
            return AnalyzerOutput(
                sarif={}, status="error",
                error="depcruise not found. Run scripts/setup.sh first.",
            )
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("depcruiser"))
        # Unlike jscpd (which reads a report file back out of its tmpdir), depcruise
        # consumes the config only at startup and writes its result to stdout, so the
        # tmpdir is intentionally released as soon as the subprocess returns — `result`
        # is fully materialised and the branches below need no tmpdir access.
        with tempfile.TemporaryDirectory(prefix="code-review-depcruiser-") as tmpdir:
            config_path = Path(tmpdir) / "cruise-config.cjs"
            config_path.write_text(_CRUISE_CONFIG, encoding="utf-8")
            cmd = (
                "node", str(binary),
                "--config", str(config_path),
                "--output-type", "json",
                *request.target_paths,
            )
            result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="depcruise timed out")
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"depcruise exited {result.returncode}: {stderr}",
            )
        try:
            data: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
