from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "skills" / "code-review"
_NODE_MODULES = _SKILL_DIR / "node_modules"


def node_binary(tool: str) -> Path | None:
    """Return path to vendored Node.js binary, or None if not installed."""
    candidate = _NODE_MODULES / ".bin" / tool
    return candidate if candidate.exists() else None


def probe_js_adapter(tool: str) -> dict[str, Any]:
    """Return capabilities probe dict for a JS/Node.js adapter."""
    if shutil.which("node") is None:
        return {"status": "unavailable", "error": "node not found on PATH"}
    binary = node_binary(tool)
    if binary is None:
        return {
            "status": "unavailable",
            "error": f"{tool} not in {_NODE_MODULES / '.bin'}. Run scripts/setup.sh first.",
        }
    return {"status": "available", "error": None}
