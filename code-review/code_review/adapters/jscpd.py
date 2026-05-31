from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path
from typing import ClassVar

from code_review.adapters.js_base import has_js_files, node_binary
from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest
from code_review.status import Status

# G1 (settled in s1-t2): jscpd is intentionally JS-scoped (lang_select._JS_ADAPTERS;
# capabilities languages=[javascript, typescript]) — duplication detection is a
# deliberately JS-only feature. By default jscpd auto-detects ~150 formats and leaks
# into HTML/CSS/etc. on real apps (the scope leak is in the invocation's format args,
# not the selector). Pinning --format to exactly the JS/TS set confines detection to the
# intended scope and nothing else.
_JS_FORMAT = "javascript,jsx,typescript,tsx"


class JscpdAdapter:
    name: ClassVar[str] = "jscpd"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "jscpd"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        binary = node_binary("jscpd")
        if binary is None:
            # Missing vendored binary → provisioning gap, not a scan failure (ADR-0019).
            return CaptureOutput.unavailable(
                "jscpd", "jscpd not found in vendored node_modules. Run scripts/setup.sh first."
            )
        if not request.target_paths:
            return CaptureOutput.unavailable("jscpd", "no target paths to analyse")
        # JS-only by design (G1) — skip cleanly on a no-JS target rather than run the
        # out-of-scope language duplication jscpd is capable of (ADR-0019). Defense in
        # depth for the all-analyzer / --target path that bypasses the selector's
        # language filter; mirrors eslint.
        if not has_js_files(request.target_paths):
            return CaptureOutput.unavailable(
                "jscpd", "no JavaScript/TypeScript files in target"
            )
        # jscpd's json reporter has no stdout mode: it treats --output as a *directory* it
        # writes jscpd-report.json into (pointing it at /dev/stdout fails, and the redirect
        # is unreliable under sandboxed/containerised environments anyway). So run it into a
        # TemporaryDirectory and splice the report file onto the capture's stdout verbatim —
        # the thin runner's payload for jscpd is that report (ADR-0020, no parse).
        with tempfile.TemporaryDirectory(prefix="code-review-jscpd-") as tmp:
            cmd = (
                "node", str(binary),
                "--reporters", "json",
                "--output", tmp,
                "--format", _JS_FORMAT,  # G1 scope pin
                "--silent",
                *request.target_paths,
            )
            capture = await run_and_capture("jscpd", *cmd, timeout_s=self.default_timeout_s)
            if capture.status is not Status.OK:
                # Failed/timed-out run wrote no usable report — pass the raw capture through.
                return capture
            report = Path(tmp) / "jscpd-report.json"
            if not report.exists():
                # jscpd exited 0 but produced no report (e.g. a silent format mismatch). An
                # empty stdout would read downstream as "ran, found nothing" and mask the
                # anomaly — flip it to error so s1-t3's bundle does not serialise the silence
                # as a clean result.
                return dataclasses.replace(
                    capture, status=Status.ERROR, error="jscpd produced no report file"
                )
            return dataclasses.replace(capture, stdout=report.read_text(errors="replace"))
