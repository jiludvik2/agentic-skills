"""s3-t2: AGENTS.md is the canonical cross-agent policy file at the repo root.
It must exist, carry a top-level heading, and cross-link the SDLC and the skill
bundle so any agent (Copilot/Cursor/Codex/Claude/…) can find the workflow."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"


def test_agents_md_exists() -> None:
    assert AGENTS_MD.exists(), f"AGENTS.md not found at {AGENTS_MD}"
    assert AGENTS_MD.read_text(encoding="utf-8").strip(), "AGENTS.md must be non-empty"


def test_agents_md_has_top_level_heading() -> None:
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert any(line.startswith("# ") for line in text.splitlines()), (
        "AGENTS.md must have a top-level '# ' heading (agents.md format)"
    )


def test_agents_md_crosslinks_sdlc_and_skill() -> None:
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "sdlc/SDLC.md" in text, "AGENTS.md must link to sdlc/SDLC.md"
    assert ".claude/skills/code-review/SKILL.md" in text, (
        "AGENTS.md must link to the skill bundle .claude/skills/code-review/SKILL.md"
    )
