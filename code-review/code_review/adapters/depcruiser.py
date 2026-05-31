from __future__ import annotations

import tempfile
from pathlib import Path
from typing import ClassVar

from code_review.adapters.js_base import node_binary
from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest

# dependency-cruiser refuses to run without a config (it aborts with "Can't open
# a config file"), so the adapter supplies its own rather than requiring the host
# target to ship a .dependency-cruiser.cjs (s3-t1). Two deliberate choices:
#   - enhancedResolveOptions.extensions (NOT tsConfig): lets depcruise resolve
#     bare ./foo TS/JS imports so circular edges are seen, without hard-requiring
#     a tsconfig.json that arbitrary targets won't have.
#   - no `forbidden` rules: the JSON output carries each dependency's `circular`
#     flag directly; a forbidden rule would make depcruise exit non-zero on a
#     violation, which the raw-capture contract would classify as an error.
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


class DependencyCruiserAdapter:
    name: ClassVar[str] = "depcruiser"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 90
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "depcruise"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        binary = node_binary("depcruise")
        if binary is None:
            # Missing vendored binary → provisioning gap, not a scan failure (ADR-0019).
            return CaptureOutput.unavailable(
                "depcruiser",
                "depcruise not found in vendored node_modules. Run scripts/setup.sh first.",
            )
        if not request.target_paths:
            return CaptureOutput.unavailable("depcruiser", "no target paths to analyse")
        # depcruise consumes the config only at startup and writes its dependency graph to
        # stdout, so the tmpdir is released as soon as run_and_capture returns (the capture
        # is fully materialised by then). The directory target is passed verbatim; depcruise
        # uses the vendored TypeScript transpiler to enumerate .ts/.tsx within it.
        with tempfile.TemporaryDirectory(prefix="code-review-depcruiser-") as tmpdir:
            config_path = Path(tmpdir) / "cruise-config.cjs"
            config_path.write_text(_CRUISE_CONFIG, encoding="utf-8")
            cmd = (
                "node", str(binary),
                "--config", str(config_path),
                "--output-type", "json",
                *request.target_paths,
            )
            return await run_and_capture(
                "depcruiser", *cmd, timeout_s=self.default_timeout_s
            )
