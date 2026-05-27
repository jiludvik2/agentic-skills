from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from radon.complexity import cc_visit  # type: ignore[import-untyped]

from code_review.adapters.sarif_utils import collect_python_files as _collect_python_files
from code_review.adapters.sarif_utils import empty_sarif
from code_review.contracts import AnalyzerOutput, MetricSet, ReviewRequest


def _analyse_file(path: Path) -> dict[str, Any] | None:
    try:
        code = path.read_text(encoding="utf-8", errors="replace")
        results = cc_visit(code)
    except Exception:
        return None
    if not results:
        return None
    functions = [
        {"name": r.name, "cc": r.complexity, "lineno": r.lineno, "rank": r.letter}
        for r in results
    ]
    return {
        "functions": functions,
        "max_cc": max(f["cc"] for f in functions),
        "average_cc": sum(f["cc"] for f in functions) / len(functions),
    }


class RadonAdapter:
    name: ClassVar[str] = "radon"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(
                sarif=empty_sarif("radon", "6.0.1"),
                metrics=MetricSet(per_file={}, per_class={}, coupling={}),
            )
        files = _collect_python_files(request.target_paths)
        per_file: dict[str, dict[str, Any]] = {}
        for f in files:
            entry = _analyse_file(f)
            if entry is not None:
                per_file[str(f)] = entry

        metrics = MetricSet(per_file=per_file, per_class={}, coupling={})
        return AnalyzerOutput(sarif=empty_sarif("radon", "6.0.1"), metrics=metrics)
