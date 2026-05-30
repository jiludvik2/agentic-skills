"""The review bundle — the thin invocation runner's agent-facing contract (ADR-0020).

A ``ReviewBundle`` aggregates the ``ReviewRequest`` echo (scope/diff/targets/languages)
with one raw ``CaptureOutput`` per tool, and serialises to deterministic JSON validated
against the published schema ``review-bundle.v1.json``. The schema constrains *structure*
(fields, the ADR-0019 status enum) — never the content of ``stdout``/``stderr``, which is
deliberately opaque (the agent interprets the raw tool output).

Additive in s0: the live CLI still emits SARIF; s2 switches it onto this bundle.
"""

from __future__ import annotations

import importlib.resources
import json
from dataclasses import dataclass
from typing import Any

from code_review.capture import CaptureOutput
from code_review.contracts import ReviewRequest

# Versioned contract id — bump on any breaking shape change (the agent/SKILL.md pin it).
SCHEMA_ID = "polyreview/review-bundle/v1"

# Published schema, shipped alongside the SARIF schema (pyproject wheel `include`).
_SCHEMA_RESOURCE = "review-bundle.v1.json"


@dataclass(frozen=True)
class ReviewBundle:
    """The request echo + one raw capture per tool."""

    request: ReviewRequest
    outputs: tuple[CaptureOutput, ...]

    def to_dict(self) -> dict[str, Any]:
        """Deterministic, schema-shaped dict. ``config`` is intentionally not echoed."""
        return {
            "schema": SCHEMA_ID,
            "request": {
                "scope": self.request.scope,
                "diff_range": self.request.diff_range,
                "target_paths": list(self.request.target_paths),
                # frozenset → sorted list so serialisation is deterministic
                "languages": sorted(self.request.languages),
            },
            "outputs": [_capture_to_dict(c) for c in self.outputs],
        }


def _capture_to_dict(capture: CaptureOutput) -> dict[str, Any]:
    return {
        "tool": capture.tool,
        "status": capture.status,
        "exit_code": capture.exit_code,
        "stdout": capture.stdout,
        "stderr": capture.stderr,
        "error": capture.error,
        "command": list(capture.command),
        "duration_s": capture.duration_s,
    }


def bundle_to_json(bundle: ReviewBundle) -> str:
    """Serialise to stable JSON (sorted keys). ``ensure_ascii=False`` keeps raw stdout
    (which may carry Unicode) byte-faithful."""
    return json.dumps(bundle.to_dict(), sort_keys=True, ensure_ascii=False)


def load_bundle_schema() -> dict[str, Any]:
    """Load the published bundle JSON schema from the package data."""
    resource = importlib.resources.files("code_review").joinpath(
        "schemas", _SCHEMA_RESOURCE
    )
    schema: dict[str, Any] = json.loads(resource.read_text(encoding="utf-8"))
    return schema
