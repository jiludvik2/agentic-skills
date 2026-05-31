from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import ClassVar

from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest
from code_review.paths import cache_root


def _semgrep_rules_dir() -> Path:
    # Resolve through cache_root() (ADR-0015) so this consumer honors
    # $POLYREVIEW_CACHE_DIR exactly like the producer (scripts/prefetch_caches.py)
    # that provisions the vendored ruleset here.
    return cache_root() / "cache" / "semgrep" / "rules"


class SemgrepAdapter:
    name: ClassVar[str] = "semgrep"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "semgrep"

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        if not request.target_paths:
            return CaptureOutput.unavailable("semgrep", "no target paths to analyse")
        if shutil.which(self.required_binary) is None:
            return CaptureOutput.unavailable("semgrep", "semgrep not found on PATH")

        # Resolve rules: explicit config override → provisioned local cache. No
        # `--config auto` fallback (incompatible with `--metrics off`, and a silent empty
        # success on a security analyzer is worse than a loud, fixable skip). ADR-0016.
        # A missing ruleset/config is a provisioning gap → unavailable (ADR-0019), carrying
        # the actionable reason — not a scan error.
        rules_override: str | None = request.config.get("semgrep_rules")
        if rules_override:
            if not Path(rules_override).exists():
                return CaptureOutput.unavailable(
                    "semgrep",
                    f"semgrep_rules override path not found: {rules_override}. "
                    "Fix the semgrep_rules value in code-review.toml.",
                )
            config_arg = rules_override
        else:
            default_rules = _semgrep_rules_dir()
            if not default_rules.is_dir():
                return CaptureOutput.unavailable(
                    "semgrep",
                    f"semgrep rules not found at {default_rules}. Run scripts/setup.sh "
                    "to provision the vendored ruleset, or set semgrep_rules in "
                    "code-review.toml.",
                )
            config_arg = str(default_rules)

        cmd = (
            "semgrep", "--sarif",
            "--config", config_arg,
            "--metrics", "off",
            # Load-bearing: disables semgrep's default .semgrepignore patterns, which
            # otherwise exclude tests/ (and vendor/, etc.) — paths we DO want scanned when
            # the diff or target points at them. Dropping it silently loses all
            # test-directory findings (verified: zero results without it). Experimental
            # "--x-" flag; validated on the pinned semgrep 1.161.0 — re-confirm on a bump.
            # (ADR-0016: kept per its scan-scope caveat.)
            "--x-ignore-semgrepignore-files",
            *request.target_paths,
        )
        with tempfile.TemporaryDirectory(prefix="code-review-semgrep-") as _tmp:
            tmp = Path(_tmp)
            env = {
                **os.environ,
                # Redirect semgrep's log/settings files so it never writes to ~/.semgrep
                "SEMGREP_LOG_FILE": str(tmp / "semgrep.log"),
                "SEMGREP_SETTINGS_FILE": str(tmp / "settings.yaml"),
            }
            # semgrep exits 0 (clean) or 1 (findings present) — both are success.
            return await run_and_capture(
                "semgrep", *cmd,
                timeout_s=self.default_timeout_s,
                env=env,
                ok_exit_codes=(0, 1),
            )
