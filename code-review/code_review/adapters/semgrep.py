from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, ClassVar

import jsonschema

from code_review.adapters.base import run_subprocess
from code_review.adapters.sarif_utils import normalise_sarif as _normalise
from code_review.contracts import AnalyzerOutput, ReviewRequest

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "sarif-2.1.0.json"
_sarif_schema: dict[str, Any] | None = None

_DEFAULT_RULES = (
    Path(__file__).resolve().parent.parent.parent
    / ".claude"
    / "skills"
    / "code-review"
    / "cache"
    / "semgrep"
    / "rules"
)


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

        # Resolve rules: config-supplied → pre-fetched local cache → auto (network)
        rules_override: str | None = request.config.get("semgrep_rules")
        if rules_override and Path(rules_override).exists():
            config_arg = rules_override
        elif _DEFAULT_RULES.is_dir():
            config_arg = str(_DEFAULT_RULES)
        else:
            config_arg = "auto"

        cmd = (
            "semgrep", "--sarif",
            "--config", config_arg,
            "--metrics", "off",
            # Bypass semgrep's built-in default ignore patterns (which exclude tests/)
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
