from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.sarif_utils import (
    collect_python_files,
    make_location,
    normalise_sarif,
    rel_uri,
)
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(items: list[Any]) -> dict[str, Any]:
    cwd = str(Path.cwd())
    results = [
        {
            "ruleId": f"vulture.unused-{item.typ}",
            "message": {
                "text": f"unused {item.typ} '{item.name}' ({item.confidence}% confidence)"
            },
            "locations": [make_location(rel_uri(item.filename, cwd), item.first_lineno)],
        }
        for item in items
    ]
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "vulture", "version": "2.13", "rules": []}
                    },
                    "results": results,
                }
            ]
        }
    )


class VultureAdapter:
    name: ClassVar[str] = "vulture"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(sarif=normalise_sarif({"runs": []}))
        files = collect_python_files(request.target_paths)
        if not files:
            return AnalyzerOutput(sarif=normalise_sarif({"runs": []}))
        import vulture as vulture_mod  # type: ignore[import-untyped]

        v = vulture_mod.Vulture()
        v.scavenge([str(f) for f in files])
        items = list(v.get_unused_code())
        return AnalyzerOutput(sarif=_to_sarif(items))
