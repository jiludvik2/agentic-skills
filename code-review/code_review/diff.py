from __future__ import annotations

from pathlib import Path

from code_review.adapters.base import run_subprocess


async def resolve_diff_paths(repo_root: Path, diff_range: str) -> tuple[str, ...]:
    """Return repo-relative paths changed in `diff_range`, via git diff --name-only."""
    result = await run_subprocess(
        "git", "diff", "--name-only", diff_range, cwd=str(repo_root)
    )
    if result.error is not None or result.timed_out or result.returncode != 0:
        return ()
    lines = result.stdout.decode(errors="replace").splitlines()
    return tuple(line.strip() for line in lines if line.strip())
