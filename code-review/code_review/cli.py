from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

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


@app.command()
def main(
    analyzer: Optional[str] = typer.Option(None, "--analyzer", help="Analyzer to run"),
    target: Optional[str] = typer.Option(None, "--target", help="Target path to analyse"),
    diff: Optional[str] = typer.Option(None, "--diff", help="Git diff range to scope analysis"),
    output: Optional[str] = typer.Option(None, "--output", help="Output file path (must be within CWD)"),
    capabilities: bool = typer.Option(False, "--capabilities", help="Print available analyzers as JSON and exit"),
) -> None:
    if capabilities:
        typer.echo(json.dumps({"analyzers": []}))
        raise typer.Exit(0)

    if output is not None:
        _guard_output_in_cwd(output)

    if analyzer is None:
        typer.echo("Error: --analyzer is required", err=True)
        raise typer.Exit(1)

    typer.echo(f"Error: no adapter registered for '{analyzer}'", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
