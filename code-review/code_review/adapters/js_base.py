from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from code_review.paths import node_modules_dir as _node_modules


def node_binary(tool: str) -> Path | None:
    """Return path to vendored Node.js binary, or None if not installed."""
    candidate = _node_modules() / ".bin" / tool
    return candidate if candidate.exists() else None


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
