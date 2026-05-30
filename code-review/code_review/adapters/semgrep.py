from __future__ import annotations

import contextlib
import importlib.resources
import json
import os
import tempfile
from pathlib import Path
from typing import Any, ClassVar

import jsonschema

from code_review.adapters.base import run_subprocess
from code_review.adapters.sarif_utils import normalise_sarif as _normalise
from code_review.contracts import AnalyzerOutput, ReviewRequest
from code_review.paths import cache_root

_SCHEMA_PATH = importlib.resources.files("code_review").joinpath("schemas", "sarif-2.1.0.json")
_sarif_schema: dict[str, Any] | None = None


def _semgrep_rules_dir() -> Path:
    # Resolve through cache_root() (ADR-0015) so this consumer honors
    # $POLYREVIEW_CACHE_DIR exactly like the producer (scripts/prefetch_caches.py)
    # that provisions the vendored ruleset here.
    return cache_root() / "cache" / "semgrep" / "rules"


def _schema() -> dict[str, Any]:
    global _sarif_schema
    if _sarif_schema is None:
        _sarif_schema = json.loads(_SCHEMA_PATH.read_text())
    return _sarif_schema


class SemgrepAdapter:
    name: ClassVar[str] = "semgrep"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "semgrep"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(sarif=_normalise({"runs": []}))

        # Resolve rules: explicit config override → provisioned local cache.
        # No `--config auto` fallback: it is incompatible with `--metrics off`
        # (semgrep: "Cannot create auto config when metrics are off"), and a
        # silent empty success on a security analyzer is worse than a loud,
        # fixable error. (ADR-0016 #3/#4)
        rules_override: str | None = request.config.get("semgrep_rules")
        if rules_override:
            # A configured override that doesn't exist is a typo, not a cue to
            # silently fall back to the cache — fail loud naming the bad path.
            if not Path(rules_override).exists():
                return AnalyzerOutput(
                    sarif={},
                    status="error",
                    error=(
                        f"semgrep_rules override path not found: {rules_override}. "
                        "Fix the semgrep_rules value in code-review.toml."
                    ),
                )
            config_arg = rules_override
        else:
            default_rules = _semgrep_rules_dir()
            if not default_rules.is_dir():
                return AnalyzerOutput(
                    sarif={},
                    status="error",
                    error=(
                        f"semgrep rules not found at {default_rules}. Run "
                        "scripts/setup.sh to provision the vendored ruleset, or set "
                        "semgrep_rules in code-review.toml."
                    ),
                )
            config_arg = str(default_rules)

        cmd = (
            "semgrep", "--sarif",
            "--config", config_arg,
            "--metrics", "off",
            # Load-bearing: disables semgrep's default .semgrepignore patterns,
            # which otherwise exclude tests/ (and vendor/, etc.) — paths we DO
            # want scanned when the diff or target points at them. Dropping it
            # silently loses all test-directory findings (verified: zero results
            # without it on tests/fixtures/). Experimental "--x-" flag; validated
            # on the pinned semgrep 1.161.0 — re-confirm on any semgrep bump.
            # (ADR-0016: kept rather than removed, per its scan-scope caveat.)
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
            result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s, env=env)

        if result.error is not None:
            msg = result.error
            if "no such file" in msg.lower() or "not found" in msg.lower():
                msg = f"semgrep not found: {msg}"
            return AnalyzerOutput(sarif={}, status="error", error=msg)

        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="error", error="semgrep timed out")

        # semgrep exits 0 (clean) or 1 (findings present) — both are success
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"semgrep exited {result.returncode}: {stderr}",
            )

        try:
            sarif: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")

        sarif = _normalise(sarif)
        with contextlib.suppress(jsonschema.ValidationError):
            jsonschema.validate(sarif, _schema())

        return AnalyzerOutput(sarif=sarif)
