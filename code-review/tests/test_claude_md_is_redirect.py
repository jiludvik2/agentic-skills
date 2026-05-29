"""s3-t2: CLAUDE.md is reduced to a thin redirect to AGENTS.md (the canonical
cross-agent policy). Guards against drift back toward duplicated policy split
between CLAUDE.md and AGENTS.md."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


def test_claude_md_exists() -> None:
    assert CLAUDE_MD.exists(), f"CLAUDE.md not found at {CLAUDE_MD}"


def test_claude_md_is_short_redirect() -> None:
    lines = [ln for ln in CLAUDE_MD.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) <= 5, (
        f"CLAUDE.md must be a thin redirect (<=5 non-blank lines); got {len(lines)}"
    )


def test_claude_md_points_at_agents_md() -> None:
    assert "AGENTS.md" in CLAUDE_MD.read_text(encoding="utf-8"), (
        "CLAUDE.md must redirect to AGENTS.md"
    )
