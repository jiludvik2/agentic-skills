from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import ClassVar

from code_review.adapters.js_base import has_js_files, node_binary
from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest
from code_review.paths import node_modules_dir

# JS complexity = radon `cc` parity for JavaScript (ADR-0022). We reuse the already-vendored
# ESLint `complexity` core rule rather than adding a tool: at threshold 0 every function
# exceeds the limit and is reported with its computed cyclomatic value, turning a violations
# rule into a full-coverage metric. The adapter ships its OWN flat config (the depcruiser
# pattern) so the host project needs none, and suppresses config lookup so the reviewed
# project's own ESLint setup cannot perturb the complexity report. JavaScript-only: ESLint
# cannot parse `.ts` without the unvendored @typescript-eslint/parser (ADR-0022 s4-t1
# amendment); `.ts` targets are silently ignored by ESLint (clean no-op).
_COMPLEXITY_CONFIG = """\
// Adapter-supplied ESLint flat config (MIT, hand-authored — same provenance policy as the
// depcruiser config). Threshold 0 reports the cyclomatic complexity of every function.
module.exports = [{ rules: { complexity: ["warn", 0] } }];
"""
_SARIF_FORMATTER = "@microsoft/eslint-formatter-sarif"


class JsComplexityAdapter:
    name: ClassVar[str] = "jscomplexity"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 90
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "eslint"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        binary = node_binary("eslint")
        if binary is None:
            # Missing vendored binary is a provisioning gap, not a scan failure (ADR-0019).
            return CaptureOutput.unavailable(
                "jscomplexity",
                "eslint not found in vendored node_modules. Run scripts/setup.sh first.",
            )
        if not request.target_paths:
            return CaptureOutput.unavailable("jscomplexity", "no target paths to analyse")
        # No JS/TS anywhere → nothing to measure (e.g. a pure-Python review). Clean skip,
        # not a spurious error (ADR-0019). (TS targets reach eslint but are ignored — JS-only.)
        if not has_js_files(request.target_paths):
            return CaptureOutput.unavailable(
                "jscomplexity", "no JavaScript/TypeScript files in target"
            )
        # Anchor eslint's cwd at the targets' common ancestor and pass relative targets —
        # the same base-path handling the eslint adapter documents (eslint ignores targets
        # outside cwd; absolute paths can mismatch realpath'd cwd through symlinks). The
        # adapter's own config is passed via --config + --no-config-lookup, so the host
        # project's eslint.config.* is never discovered or merged.
        abs_targets = [os.path.abspath(p) for p in request.target_paths]
        anchor = os.path.commonpath(abs_targets)
        if not os.path.isdir(anchor):
            anchor = os.path.dirname(anchor)
        rel_targets = tuple(os.path.relpath(p, anchor) for p in abs_targets)
        # The complexity flat config is consumed at startup; the tmpdir is released as soon
        # as run_and_capture returns (the SARIF capture is fully materialised by then).
        with tempfile.TemporaryDirectory(prefix="code-review-jscomplexity-") as tmpdir:
            config_path = Path(tmpdir) / "complexity.config.cjs"
            config_path.write_text(_COMPLEXITY_CONFIG, encoding="utf-8")
            cmd = (
                "node", str(binary),
                "--no-config-lookup",
                "--config", str(config_path),
                "--format", _SARIF_FORMATTER,
                *rel_targets,
            )
            # The SARIF formatter is a vendored package loaded by name; the anchored cwd is
            # the reviewed project (no node_modules), so export the vendored dir as NODE_PATH
            # so it resolves regardless of where the target lives (mirrors the eslint adapter).
            env = dict(os.environ)
            vendored = str(node_modules_dir())
            existing = env.get("NODE_PATH")
            env["NODE_PATH"] = os.pathsep.join([vendored, existing]) if existing else vendored
            # eslint exits 0 (warnings/clean) or 1 (errors present); both are success for raw
            # capture. 2 (config/crash) is left untolerated → surfaces as error (ADR-0019).
            return await run_and_capture(
                "jscomplexity", *cmd,
                timeout_s=self.default_timeout_s,
                cwd=anchor,
                env=env,
                ok_exit_codes=(0, 1),
            )
