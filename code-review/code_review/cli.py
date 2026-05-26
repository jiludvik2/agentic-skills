from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import shutil
from enum import StrEnum
from pathlib import Path
from typing import Any

import jsonschema
import typer

from code_review.aggregator import aggregate
from code_review.config import load_config
from code_review.contracts import AnalyzerOutput, MetricSet, ReviewRequest
from code_review.diff import resolve_diff_paths
from code_review.hotspots import compute_hotspots

app = typer.Typer(add_completion=False)

_SKILL_DIR = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "code-review"
_CAPABILITIES_PATH = _SKILL_DIR / "capabilities.json"
_SCHEMA_PATH = _SKILL_DIR / "schemas" / "review-response.json"


class ReviewScope(StrEnum):
    lite = "lite"
    standard = "standard"
    full = "full"


def _probe_analyzer(adapter_cls: type[Any]) -> dict[str, Any]:
    """Recompute runtime availability for one analyzer.

    Subprocess-based adapters declare a ``required_binary`` ClassVar; if the binary is
    absent from PATH they are unavailable. Library-based adapters (no ``required_binary``)
    are always available since their dependency is pinned in the package.
    """
    binary = getattr(adapter_cls, "required_binary", None)
    if binary is None:
        return {"status": "available", "error": None}
    if shutil.which(binary) is None:
        return {"status": "unavailable", "error": f"{binary} not found on PATH"}
    return {"status": "available", "error": None}


def _build_capabilities() -> dict[str, Any]:
    from code_review.adapters import REGISTRY

    static = json.loads(_CAPABILITIES_PATH.read_text(encoding="utf-8"))
    runtime = {name: _probe_analyzer(cls) for name, cls in REGISTRY.items()}
    return {"static": static, "analyzers": runtime}


def _guard_output_in_cwd(output: str) -> None:
    resolved = Path(output).resolve()
    cwd = Path.cwd().resolve()
    if not resolved.is_relative_to(cwd):
        typer.echo(
            f"Output path '{output}' is outside CWD (sandbox restriction). "
            "Use a path within the current working directory.",
            err=True,
        )
        raise typer.Exit(1)


def _output_to_dict(output: AnalyzerOutput) -> dict[str, Any]:
    return {
        "sarif": output.sarif,
        "metrics": dataclasses.asdict(output.metrics) if output.metrics is not None else None,
        "duration_s": output.duration_s,
        "status": output.status,
        "error": output.error,
    }


async def _safe_run(adapter: Any, request: ReviewRequest) -> AnalyzerOutput:
    try:
        return await adapter.run(request)  # type: ignore[no-any-return]
    except Exception as exc:
        return AnalyzerOutput(sarif={}, status="error", error=str(exc))


def _merge_metrics(outputs: list[AnalyzerOutput]) -> MetricSet | None:
    # Last-write-wins per file key; analyzers are expected to report disjoint files.
    merged: MetricSet | None = None
    for out in outputs:
        if out.metrics is None:
            continue
        if merged is None:
            merged = MetricSet(
                per_file=dict(out.metrics.per_file),
                per_class=dict(out.metrics.per_class),
                coupling=dict(out.metrics.coupling),
            )
        else:
            merged.per_file.update(out.metrics.per_file)
            merged.per_class.update(out.metrics.per_class)
            merged.coupling.update(out.metrics.coupling)
    return merged


async def _run_analyzers(
    names: list[str],
    target: str | None,
    diff: str | None = None,
    scope: str = "lite",
    line_tolerance: int = 3,
    hotspot_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    from code_review.adapters import REGISTRY

    if diff is not None:
        target_paths = await resolve_diff_paths(Path.cwd(), diff)
        diff_files: set[str] | None = set(target_paths)
    elif target is not None:
        target_paths = (target,)
        diff_files = None
    else:
        target_paths = (".",)
        diff_files = None

    request = ReviewRequest(
        scope=scope,
        diff_range=diff,
        target_paths=target_paths,
        languages=frozenset(),
        config={},
    )

    task_map: dict[str, asyncio.Task[AnalyzerOutput]] = {}
    async with asyncio.TaskGroup() as tg:
        for name in names:
            task_map[name] = tg.create_task(_safe_run(REGISTRY[name](), request))

    per_analyzer = {name: t.result() for name, t in task_map.items()}
    outputs = list(per_analyzer.values())

    consolidated_sarif = aggregate(outputs, line_tolerance=line_tolerance)
    merged_metrics = _merge_metrics(outputs)
    hotspots = compute_hotspots(
        consolidated_sarif,
        merged_metrics,
        diff_files=diff_files,
        weights=hotspot_weights,
    )

    return {
        "sarif": consolidated_sarif,
        "metrics": dataclasses.asdict(merged_metrics) if merged_metrics is not None else None,
        "ranked_hotspots": hotspots,
        "analyzers": {name: _output_to_dict(out) for name, out in per_analyzer.items()},
    }


@app.command()
def main(
    analyzer: list[str] = typer.Option(
        [], "--analyzer", help="Analyzer to run (repeat for multiple)"
    ),
    target: str | None = typer.Option(None, "--target", help="Target path to analyse"),
    diff: str | None = typer.Option(None, "--diff", help="Git diff range to scope analysis"),
    output: str | None = typer.Option(
        None, "--output", help="Output file path (must be within CWD)"
    ),
    review_scope: ReviewScope | None = typer.Option(
        None, "--review-scope", help="Review depth: lite, standard, or full"
    ),
    capabilities: bool = typer.Option(
        False, "--capabilities", help="Print static + runtime capabilities as JSON and exit"
    ),
) -> None:
    if capabilities:
        typer.echo(json.dumps(_build_capabilities()))
        raise typer.Exit(0)

    if output is not None:
        _guard_output_in_cwd(output)

    if not analyzer:
        typer.echo("Error: --analyzer is required", err=True)
        raise typer.Exit(1)

    from code_review.adapters import REGISTRY

    unknown = [n for n in analyzer if n not in REGISTRY]
    if unknown:
        typer.echo(f"Error: unknown analyzer(s): {', '.join(unknown)}", err=True)
        raise typer.Exit(1)

    config = load_config(_SKILL_DIR)
    scope = review_scope.value if review_scope is not None else "lite"
    result = asyncio.run(
        _run_analyzers(
            analyzer,
            target,
            diff,
            scope,
            line_tolerance=config.dedup_line_tolerance,
            hotspot_weights=config.hotspot_weights,
        )
    )
    analyzers_dict: dict[str, Any] = result["analyzers"]
    has_error = any(v["status"] == "error" for v in analyzers_dict.values())

    if _SCHEMA_PATH.exists():
        try:
            schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.validate(instance=result, schema=schema)
        except jsonschema.ValidationError as exc:
            typer.echo(f"schema validation warning: {exc.message}", err=True)

    json_content = json.dumps(result)

    if output is not None:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = output_path.parent / (output_path.name + ".tmp")
        tmp_file.write_text(json_content)
        os.rename(tmp_file, output_path)
        n_findings = sum(
            len(run.get("results", []))
            for run in result.get("sarif", {}).get("runs", [])
        )
        total_s = sum(v.get("duration_s", 0.0) for v in analyzers_dict.values())
        typer.echo(
            f"analyzers: {len(analyzers_dict)} | findings: {n_findings} "
            f"| duration: {total_s:.2f}s"
        )
    else:
        typer.echo(json_content)

    if has_error:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
