from __future__ import annotations

import asyncio
import dataclasses
import json
from pathlib import Path
from typing import Any, Optional

import typer

from code_review.contracts import AnalyzerOutput, ReviewRequest

app = typer.Typer(add_completion=False)


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


async def _run_analyzers(
    names: list[str],
    target: str | None,
) -> dict[str, Any]:
    from code_review.adapters import REGISTRY

    target_paths: tuple[str, ...] = (target,) if target else (".",)
    request = ReviewRequest(
        scope="standard",
        diff_range=None,
        target_paths=target_paths,
        languages=frozenset(),
        config={},
    )

    task_map: dict[str, asyncio.Task[AnalyzerOutput]] = {}
    async with asyncio.TaskGroup() as tg:
        for name in names:
            task_map[name] = tg.create_task(REGISTRY[name]().run(request))

    return {
        "analyzers": {name: _output_to_dict(t.result()) for name, t in task_map.items()}
    }


@app.command()
def main(
    analyzer: list[str] = typer.Option([], "--analyzer", help="Analyzer to run (repeat for multiple)"),
    target: Optional[str] = typer.Option(None, "--target", help="Target path to analyse"),
    diff: Optional[str] = typer.Option(None, "--diff", help="Git diff range to scope analysis"),
    output: Optional[str] = typer.Option(None, "--output", help="Output file path (must be within CWD)"),
    capabilities: bool = typer.Option(False, "--capabilities", help="Print available analyzers as JSON and exit"),
) -> None:
    if capabilities:
        from code_review.adapters import REGISTRY
        typer.echo(json.dumps({"analyzers": list(REGISTRY.keys())}))
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

    result = asyncio.run(_run_analyzers(analyzer, target))
    typer.echo(json.dumps(result))


if __name__ == "__main__":
    app()
