from __future__ import annotations

import asyncio
import importlib.resources
import json
import os
import shutil
from enum import StrEnum
from pathlib import Path
from typing import Any

import jsonschema
import typer

from code_review.capture import CaptureOutput
from code_review.config import ConfigError, load_config
from code_review.contracts import ReviewRequest
from code_review.diff import resolve_diff_paths
from code_review.review_bundle import ReviewBundle, bundle_to_json, load_bundle_schema
from code_review.selector import resolve_review_selection
from code_review.status import Status

app = typer.Typer(add_completion=False)

_CAPABILITIES_PATH = importlib.resources.files("code_review").joinpath("capabilities.json")


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


async def _safe_run(adapter: Any, request: ReviewRequest, name: str) -> CaptureOutput:
    """Run one adapter, never raising: a crash becomes an ``error`` capture for ``name`` so
    one broken analyzer cannot take down the whole run (ADR-0019/0020)."""
    try:
        return await adapter.run(request)  # type: ignore[no-any-return]
    except Exception as exc:
        return CaptureOutput(tool=name, status=Status.ERROR, error=str(exc))


async def _run_analyzers(
    names: list[str],
    target: str | None,
    diff: str | None = None,
    scope: str = "per-task",
    semgrep_rules: str | None = None,
) -> ReviewBundle:
    """Collect one raw ``CaptureOutput`` per selected analyzer into a ``ReviewBundle`` — the
    thin-runner contract (ADR-0020). No SARIF aggregation, no findings parsing."""
    from code_review.adapters import REGISTRY

    if diff is not None:
        target_paths = await resolve_diff_paths(Path.cwd(), diff)
    elif target is not None:
        target_paths = (target,)
    else:
        target_paths = (".",)

    request = ReviewRequest(
        scope=scope,
        diff_range=diff,
        target_paths=target_paths,
        languages=frozenset(),
        config={
            "semgrep_rules": semgrep_rules,
        },
    )

    task_map: dict[str, asyncio.Task[CaptureOutput]] = {}
    async with asyncio.TaskGroup() as tg:
        for name in names:
            task_map[name] = tg.create_task(_safe_run(REGISTRY[name](), request, name))

    # Preserve selection order so the bundle is deterministic.
    captures = tuple(task_map[name].result() for name in names)
    return ReviewBundle(request=request, outputs=captures)


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
def run(
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

    bundle = asyncio.run(
        _run_analyzers(
            names,
            target,
            diff,
            timing_scope,
            semgrep_rules=config.semgrep_rules,
        )
    )
    captures = bundle.outputs
    # Exit non-zero when any tool failed to produce a usable result. `error` and `timeout`
    # both count (a timed-out tool analysed nothing); `unavailable` is a benign clean skip
    # (ADR-0019) and stays exit 0, as does an all-`ok` run.
    has_error = any(c.status in (Status.ERROR, Status.TIMEOUT) for c in captures)

    json_content = bundle_to_json(bundle)
    # The bundle is schema-shaped by construction; validate the actually-emitted JSON
    # defensively and warn (never crash) so a contract drift is surfaced without losing the
    # captured output.
    try:
        jsonschema.validate(instance=json.loads(json_content), schema=load_bundle_schema())
    except jsonschema.ValidationError as exc:
        typer.echo(f"schema validation warning: {exc.message}", err=True)

    if output is not None:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = output_path.parent / (output_path.name + ".tmp")
        tmp_file.write_text(json_content)
        os.rename(tmp_file, output_path)
        # The runner emits no parsed findings — summarise per-tool status counts + total
        # duration instead.
        counts: dict[str, int] = {}
        for c in captures:
            key = Status(c.status).value
            counts[key] = counts.get(key, 0) + 1
        status_summary = ", ".join(f"{k}: {counts[k]}" for k in sorted(counts))
        total_s = sum(c.duration_s for c in captures)
        typer.echo(
            f"analyzers: {len(captures)} | {status_summary} | duration: {total_s:.2f}s"
        )
    else:
        typer.echo(json_content)

    if has_error:
        raise typer.Exit(1)


@app.command()
def install(
    agent: list[str] = typer.Option(
        [],
        "--agent",
        help="Install to a specific agent target (repeat/comma for many): "
        "agents, claude, copilot, gemini. Default: agents + every agent home present.",
    ),
    all_targets: bool = typer.Option(
        False, "--all", help="Install to every registry target (creates each home)."
    ),
    force: bool = typer.Option(
        False, "--force", help="Refresh an already-installed bundle in place (remove-then-copy)."
    ),
) -> None:
    """Copy the skill bundle into the user-level skills dir(s) (ADR-0018)."""
    from code_review.install import TargetResult, resolve_targets
    from code_review.install import install as do_install

    # Allow comma-separated --agent values (e.g. --agent claude,copilot).
    agents = [a.strip() for raw in agent for a in raw.split(",") if a.strip()]
    try:
        targets = resolve_targets(agents or None, all_targets)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    try:
        results: list[TargetResult] = do_install(targets, force=force)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    for r in results:
        typer.echo(f"{r.action:9} {r.dest}")

    refused = [r for r in results if r.action == "refused"]
    if refused:
        for r in refused:
            typer.echo(
                f"Error: {r.dest} exists but is not a code-review bundle; "
                "not overwritten (use a clean target or remove it first).",
                err=True,
            )

    typer.echo(
        "\nNext: provision analyzer caches (node_modules, Trivy DB) by running "
        "the bundle's setup.sh — install places the skill; it does not fetch caches."
    )

    if refused:
        raise typer.Exit(1)


@app.command()
def uninstall(
    agent: list[str] = typer.Option(
        [],
        "--agent",
        help="Uninstall from a specific agent target (repeat/comma for many): "
        "agents, claude, copilot, gemini. Default: agents + every agent home present.",
    ),
    all_targets: bool = typer.Option(
        False, "--all", help="Uninstall from every registry target."
    ),
) -> None:
    """Remove the skill bundle from the user-level skills dir(s) (ADR-0018 §5).

    Marker-gated: only a directory that is verifiably our bundle is removed. Siblings,
    the agent's reviewer sub-agent, the skills dir itself, and agent homes are never
    touched. A target that exists but fails the marker check is refused (left intact)
    and the run exits non-zero; clean removals and genuine no-ops keep exit 0.
    """
    from code_review.install import TargetResult, resolve_targets
    from code_review.install import uninstall as do_uninstall

    # Allow comma-separated --agent values (e.g. --agent claude,copilot).
    agents = [a.strip() for raw in agent for a in raw.split(",") if a.strip()]
    try:
        targets = resolve_targets(agents or None, all_targets)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    results: list[TargetResult] = do_uninstall(targets)

    for r in results:
        typer.echo(f"{r.action:9} {r.dest}")

    refused = [r for r in results if r.action == "refused"]
    removed = [r for r in results if r.action == "removed"]

    if not removed and not refused:
        typer.echo("nothing to uninstall")

    for r in refused:
        typer.echo(
            f"Error: {r.dest} exists but is not a code-review bundle "
            "(marker check failed); left intact.",
            err=True,
        )

    if refused:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
