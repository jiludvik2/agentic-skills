from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.sarif_utils import (
    collect_python_files,
    empty_sarif,
    make_location,
    normalise_sarif,
    rel_uri,
)
from code_review.contracts import AnalyzerOutput, MetricSet, ReviewRequest

_LOW_COHESION_THRESHOLD = 50.0


def _analyse_file(path: Path) -> dict[str, dict[str, Any]]:
    try:
        from cohesion.module import Module  # type: ignore[import-untyped]

        m = Module.from_file(str(path))
        return {
            cls_name: {"cohesion": data["cohesion"], "lineno": data["lineno"]}
            for cls_name, data in m.structure.items()
        }
    except Exception:
        return {}


class CohesionAdapter:
    name: ClassVar[str] = "cohesion"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(
                sarif=empty_sarif("cohesion", "1.1.0"),
                metrics=MetricSet(per_file={}, per_class={}, coupling={}),
            )
        cwd = str(Path.cwd())
        files = collect_python_files(request.target_paths)
        per_class: dict[str, dict[str, Any]] = {}
        results = []

        for f in files:
            for cls_name, info in _analyse_file(f).items():
                key = f"{rel_uri(f, cwd)}::{cls_name}"
                per_class[key] = info
                if info["cohesion"] < _LOW_COHESION_THRESHOLD:
                    results.append(
                        {
                            "ruleId": "cohesion.low-cohesion",
                            "message": {
                                "text": (
                                    f"class '{cls_name}' has cohesion "
                                    f"{info['cohesion']:.1f}% "
                                    f"(threshold {_LOW_COHESION_THRESHOLD:.0f}%)"
                                )
                            },
                            "locations": [make_location(rel_uri(f, cwd), info["lineno"])],
                        }
                    )

        sarif = normalise_sarif(
            {
                "runs": [
                    {
                        "tool": {
                            "driver": {"name": "cohesion", "version": "1.1.0", "rules": []}
                        },
                        "results": results,
                    }
                ]
            }
        )
        return AnalyzerOutput(
            sarif=sarif,
            metrics=MetricSet(per_file={}, per_class=per_class, coupling={}),
        )
