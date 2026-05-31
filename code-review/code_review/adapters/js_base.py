from __future__ import annotations

import os
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from code_review.paths import node_modules_dir as _node_modules

# Source extensions that mark a target as having JavaScript/TypeScript to analyse.
_JS_EXTENSIONS = frozenset(
    {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}
)
# Vendored/VCS/build dirs skipped when walking a directory target for JS files.
_WALK_SKIP_DIRS = frozenset(
    {"node_modules", ".git", ".venv", "venv", "__pycache__",
     ".tox", ".mypy_cache", "dist", "build"}
)


def node_binary(tool: str) -> Path | None:
    """Return path to vendored Node.js binary, or None if not installed.

    Note: only the eslint adapter additionally exports ``NODE_PATH`` (see
    ``eslint.py``), because it is the only Node analyzer that loads a vendored
    *package* by name (the ``@microsoft/eslint-formatter-sarif`` formatter) and
    thus depends on cwd-relative module resolution. knip/jscpd/depcruiser invoke
    their own ``.bin`` entrypoint and emit JSON natively, so they have no
    equivalent exposure — the asymmetry is intentional, not an omission.
    """
    candidate = _node_modules() / ".bin" / tool
    return candidate if candidate.exists() else None


def has_js_files(paths: Iterable[str]) -> bool:
    """True if any target path is (or contains) a JavaScript/TypeScript source file.

    A directory target is walked (skipping vendored/VCS/build dirs) and
    short-circuits on the first match. A non-directory path is matched on its
    extension alone — so a single-file target, or a file deleted by a diff (which
    no longer exists on disk but is still JS *work*), counts as JS. Lets JS-only
    analyzers tell "no JS to analyse here" (→ ``unavailable``) apart from a real
    failure (ADR-0019).
    """
    for p in paths:
        if os.path.isdir(p):
            for _root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in _WALK_SKIP_DIRS]
                if any(os.path.splitext(f)[1] in _JS_EXTENSIONS for f in files):
                    return True
        elif os.path.splitext(p)[1] in _JS_EXTENSIONS:
            return True
    return False


def probe_js_adapter(tool: str) -> dict[str, Any]:
    """Return capabilities probe dict for a JS/Node.js adapter."""
    if shutil.which("node") is None:
        return {"status": "unavailable", "error": "node not found on PATH"}
    binary = node_binary(tool)
    if binary is None:
        return {
            "status": "unavailable",
            "error": (
                f"{tool} not in {_node_modules() / '.bin'}. Install vendored Node "
                "tooling with scripts/setup.sh (source checkout), or set "
                "POLYREVIEW_CACHE_DIR to a directory with a populated node_modules."
            ),
        }
    return {"status": "available", "error": None}
