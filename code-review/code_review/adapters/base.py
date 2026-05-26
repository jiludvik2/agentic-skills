from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class SubprocessResult:
    stdout: bytes
    stderr: bytes
    returncode: int
    timed_out: bool = False
    error: str | None = None


async def run_subprocess(
    *cmd: str, timeout_s: float = 60.0, cwd: str | None = None
) -> SubprocessResult:
    proc: asyncio.subprocess.Process
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
    except Exception as exc:
        return SubprocessResult(stdout=b"", stderr=b"", returncode=-1, error=str(exc))

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        rc = proc.returncode if proc.returncode is not None else -1
        return SubprocessResult(stdout=stdout, stderr=stderr, returncode=rc)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except (ProcessLookupError, OSError):
            pass
        return SubprocessResult(stdout=b"", stderr=b"", returncode=-1, timed_out=True)
    except Exception as exc:
        return SubprocessResult(stdout=b"", stderr=b"", returncode=-1, error=str(exc))
