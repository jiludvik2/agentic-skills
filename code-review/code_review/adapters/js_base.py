from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def _node_modules() -> Path:
    return Path.cwd() / ".claude" / "skills" / "code-review" / "node_modules"


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
            "error": f"{tool} not in {_node_modules() / '.bin'}. Run scripts/setup.sh first.",
        }
    return {"status": "available", "error": None}
