from __future__ import annotations

import asyncio
import dataclasses
import importlib.resources
import json
import os
import shutil
from enum import StrEnum
from pathlib import Path
from typing import Any

import jsonschema
import typer

from code_review.aggregator import aggregate
from code_review.config import ConfigError, load_config
from code_review.contracts import AnalyzerOutput, MetricSet, ReviewRequest
from code_review.diff import resolve_diff_paths
from code_review.hotspots import compute_hotspots
from code_review.selector import resolve_review_selection

app = typer.Typer(add_completion=False)

_CAPABILITIES_PATH = importlib.resources.files("code_review").joinpath("capabilities.json")
_SCHEMA_PATH = importlib.resources.files("code_review").joinpath("schemas", "review-response.json")


def _resolve_config_path(config_arg: Path | None) -> Path | None:
    """Resolve the config-file path per the CWD-relative lookup convention.

    - None + CWD has code-review.toml → return that CWD path
    - None + no CWD code-review.toml → return None (caller uses defaults)
    - Explicit Path that exists → return it (CWD ignored)
    - Explicit Path that does not exist → raise FileNotFoundError naming the path
    """
    if config_arg is None:
        cwd_toml = Path.cwd() / "code-review.toml"
        return cwd_toml if cwd_toml.exists() else None
    if not config_arg.exists():
        raise FileNotFoundError(f"--config path does not exist: {config_arg}")
    return config_arg

_VALID_DEPTHS = {"quick", "full"}


class TimingScope(StrEnum):
    per_task = "per-task"
    story_level = "story-level"


def _probe_analyzer(adapter_cls: type[Any]) -> dict[str, Any]:
    """Recompute runtime availability for one analyzer.

    JS adapters declare a ``node_tool`` ClassVar and use vendored binaries from
    node_modules; they are probed via ``probe_js_adapter``.
    Subprocess-based adapters declare a ``required_binary`` ClassVar; if the binary is
    absent from PATH they are unavailable. Library-based adapters (no ``required_binary``)
    are always available since their dependency is pinned in the package.
    """
    node_tool = getattr(adapter_cls, "node_tool", None)
    if node_tool is not None:
        from code_review.adapters.js_base import probe_js_adapter
        return probe_js_adapter(str(node_tool))
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
    per_file: dict[str, dict[str, Any]] = {}
    per_class: dict[str, dict[str, Any]] = {}
    coupling: dict[str, dict[str, Any]] = {}
    any_metrics = False
    for out in outputs:
        if out.metrics is None:
            continue
        any_metrics = True
        per_file = {**per_file, **out.metrics.per_file}
        per_class = {**per_class, **out.metrics.per_class}
        coupling = {**coupling, **out.metrics.coupling}
    if not any_metrics:
        return None
    return MetricSet(per_file=per_file, per_class=per_class, coupling=coupling)


async def _run_analyzers(
    names: list[str],
    target: str | None,
    diff: str | None = None,
    scope: str = "per-task",
    line_tolerance: int = 3,
    hotspot_weights: dict[str, float] | None = None,
    severity_overrides: dict[str, str] | None = None,
    contract_testing: dict[str, Any] | None = None,
    semgrep_rules: str | None = None,
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
        config={
            "contract_testing": contract_testing or {},
            "semgrep_rules": semgrep_rules,
        },
    )

    task_map: dict[str, asyncio.Task[AnalyzerOutput]] = {}
    async with asyncio.TaskGroup() as tg:
        for name in names:
            task_map[name] = tg.create_task(_safe_run(REGISTRY[name](), request))

    per_analyzer = {name: t.result() for name, t in task_map.items()}
    outputs = list(per_analyzer.values())

    consolidated_sarif = aggregate(
        outputs,
        line_tolerance=line_tolerance,
        severity_overrides=severity_overrides,
    )
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


def _resolve_depth(
    raw_depth_values: list[str],
) -> tuple[str, bool, list[str]]:
    """Validate and resolve a list of raw --depth values.

    Returns (resolved_depth, depth_was_explicit, warnings).
    Emits a warning when contradictory values are supplied.
    Exits non-zero immediately if any value is invalid.
    """
    warnings: list[str] = []
    if not raw_depth_values:
        return "quick", False, warnings

    invalid = [v for v in raw_depth_values if v.lower() not in _VALID_DEPTHS]
    if invalid:
        typer.echo(
            f"Error: invalid --depth value(s): {', '.join(repr(v) for v in invalid)}. "
            f"Valid values: quick, full.",
            err=True,
        )
        raise typer.Exit(1)

    normalised = [v.lower() for v in raw_depth_values]
    unique = set(normalised)
    if len(unique) == 1:
        return normalised[0], True, warnings

    # Contradictory: pick simpler
    resolved = "quick"
    warnings.append(
        f"--depth supplied multiple times with conflicting values; "
        f"using 'quick' (simpler of {', '.join(repr(v) for v in sorted(unique))})."
    )
    return resolved, True, warnings


@app.command()
def main(
    analyzer: list[str] = typer.Option(
        [], "--analyzer", help="Analyzer to run (repeat for multiple; overrides --review/--depth)"
    ),
    review: list[str] = typer.Option(
        [], "--review", help="Review domain or subcategory to select (repeat for multiple)"
    ),
    depth: list[str] = typer.Option(
        [], "--depth", help="Depth tier: quick or full (default: quick)"
    ),
    language: list[str] = typer.Option(
        [], "--language", help="Language to analyse (repeat for multiple; legacy selection mode)"
    ),
    target: str | None = typer.Option(None, "--target", help="Target path to analyse"),
    diff: str | None = typer.Option(None, "--diff", help="Git diff range to scope analysis"),
    output: str | None = typer.Option(
        None, "--output", help="Output file path (must be within CWD)"
    ),
    scope: TimingScope = typer.Option(
        TimingScope.per_task, "--scope", help="Timing scope: per-task or story-level"
    ),
    capabilities: bool = typer.Option(
        False, "--capabilities", help="Print static + runtime capabilities as JSON and exit"
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help=(
            "Path to code-review.toml. "
            "Default: ./code-review.toml in CWD if present, else built-in defaults."
        ),
    ),
) -> None:
    if capabilities:
        typer.echo(json.dumps(_build_capabilities()))
        raise typer.Exit(0)

    if output is not None:
        _guard_output_in_cwd(output)

    from code_review.adapters import REGISTRY

    resolved_depth, depth_explicit, depth_warnings = _resolve_depth(depth)
    for w in depth_warnings:
        typer.echo(w, err=True)

    if analyzer:
        # Override mode: run exactly these analyzers, skip review/depth resolution
        names = list(analyzer)
    elif review or depth or not language:
        # New review/depth selection (also the default when no --language)
        caps_data = json.loads(_CAPABILITIES_PATH.read_text(encoding="utf-8"))
        analyzer_entries = caps_data["analyzers"]

        # Normalise and deduplicate --review values
        normalised_review: list[str] = []
        seen_review: set[str] = set()
        for raw in review:
            v = raw.lower()
            if v in seen_review:
                typer.echo(
                    f"--review {raw} supplied multiple times; duplicates ignored.",
                    err=True,
                )
            else:
                seen_review.add(v)
                normalised_review.append(v)

        # Language filter: use --language as explicit filter when combined with review/depth
        diff_langs: frozenset[str] | None = frozenset(language) if language else None

        sel = resolve_review_selection(
            analyzer_entries,
            review=normalised_review,
            depth=resolved_depth,
            scope=scope.value,
            diff_languages=diff_langs,
            depth_explicit=depth_explicit,
        )

        for w in sel.warnings:
            typer.echo(w, err=True)

        if sel.error:
            typer.echo(f"Error: {sel.error}", err=True)
            raise typer.Exit(1)

        if not sel.analyzers:
            typer.echo("Error: no analyzers selected after filtering", err=True)
            raise typer.Exit(1)

        names = sel.analyzers
    else:
        # Legacy --language selection (backward compat when no --review/--depth)
        from code_review.lang_select import select_adapters
        names = select_adapters(frozenset(language))

    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        typer.echo(f"Error: unknown analyzer(s): {', '.join(unknown)}", err=True)
        raise typer.Exit(1)

    try:
        resolved_config_path = _resolve_config_path(config_path)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    try:
        config = load_config(resolved_config_path)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    disabled = set(config.disabled_analyzers)
    explicitly_disabled = [n for n in names if n in disabled]
    if explicitly_disabled:
        typer.echo(
            f"Error: analyzer(s) disabled in code-review.toml: {', '.join(explicitly_disabled)}",
            err=True,
        )
        raise typer.Exit(1)

    timing_scope = scope.value
    for name in names:
        adapter_cls = REGISTRY[name]
        restrictions: frozenset[str] = getattr(adapter_cls, "scope_restrictions", frozenset())
        if restrictions and timing_scope not in restrictions:
            allowed = ", ".join(sorted(restrictions))
            typer.echo(
                f"Error: analyzer '{name}' requires --scope {{{allowed}}} (got '{timing_scope}')",
                err=True,
            )
            raise typer.Exit(1)

    result = asyncio.run(
        _run_analyzers(
            names,
            target,
            diff,
            timing_scope,
            line_tolerance=config.dedup_line_tolerance,
            hotspot_weights=config.hotspot_weights,
            severity_overrides=config.severity_overrides,
            contract_testing=config.contract_testing,
            semgrep_rules=config.semgrep_rules,
        )
    )
    analyzers_dict: dict[str, Any] = result["analyzers"]
    has_error = any(v["status"] == "error" for v in analyzers_dict.values())

    if _SCHEMA_PATH.is_file():
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
