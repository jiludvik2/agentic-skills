from __future__ import annotations

import os
from pathlib import Path

# s0-t6 / ADR-0015: single source of truth for the operator-runtime cache base.
# Both the producer (scripts/prefetch_caches.py, scripts/setup.sh) and the
# consumers (adapters/trivy.py, adapters/js_base.py) resolve through cache_root()
# so their write and read paths cannot diverge. Anchored on CWD (matching the
# code-review.toml lookup and the --output guard), overridable via the
# POLYREVIEW_CACHE_DIR environment variable for CI / explicit deployments.
_CACHE_ENV = "POLYREVIEW_CACHE_DIR"


def cache_root() -> Path:
    """Base directory under which operator-runtime caches live.

    ``$POLYREVIEW_CACHE_DIR`` if set; otherwise CWD-anchored at
    ``./.claude/skills/code-review`` (the production-nested layout where the
    CLI runs from the host root).
    """
    env = os.environ.get(_CACHE_ENV)
    if env:
        return Path(env)
    return Path.cwd() / ".claude" / "skills" / "code-review"


def trivy_cache_dir() -> Path:
    """Where the Trivy vulnerability DB is prefetched and read from."""
    return cache_root() / "cache" / "trivy-db"


def node_modules_dir() -> Path:
    """Where vendored Node.js tooling is installed and read from."""
    return cache_root() / "node_modules"


class SkillPaths:
    def __init__(self, skill_root: Path) -> None:
        self.skill_root = skill_root

    @property
    def runs_dir(self) -> Path:
        return self.skill_root / "runs"

    @property
    def cache_dir(self) -> Path:
        return self.skill_root / "cache"
