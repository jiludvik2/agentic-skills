from __future__ import annotations

from pathlib import Path

from code_review.adapters.base import run_subprocess


async def get_repo_root(cwd: Path) -> Path:
    """Return the git repo root containing `cwd`, falling back to `cwd` if not in a repo."""
    result = await run_subprocess("git", "rev-parse", "--show-toplevel", cwd=str(cwd))
    if result.error is not None or result.timed_out or result.returncode != 0:
        return cwd
    toplevel = result.stdout.decode(errors="replace").strip()
    return Path(toplevel) if toplevel else cwd


async def resolve_diff_paths(repo_root: Path, diff_range: str) -> tuple[str, ...]:
    """Return absolute paths changed in `diff_range`, anchored on `repo_root`."""
    result = await run_subprocess(
        "git", "diff", "--name-only", diff_range, cwd=str(repo_root)
    )
    if result.error is not None or result.timed_out or result.returncode != 0:
        return ()
    lines = result.stdout.decode(errors="replace").splitlines()
    return tuple(
        str(repo_root / line.strip()) for line in lines if line.strip()
    )
