"""s2-t5: SKILL.md must lead with the installed `claude-code-review` binary,
not `python -m code_review.cli`. The module form breaks under `pipx install` /
`uv tool install` (isolated venv, package not on sys.path for arbitrary
python). The source-checkout fallback is acknowledged in a prose note only."""
from __future__ import annotations

import re
from pathlib import Path

SKILL_MD = (
    Path(__file__).parent.parent
    / ".claude" / "skills" / "code-review" / "SKILL.md"
)

# Match a fenced code block (any language tag). Group 1 is the body.
_FENCE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)


def _code_blocks() -> list[str]:
    return _FENCE.findall(SKILL_MD.read_text(encoding="utf-8"))


def _first_nonblank_line(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def test_invocation_block_leads_with_binary() -> None:
    """The Invocation section's first fenced block must lead with the binary."""
    text = SKILL_MD.read_text(encoding="utf-8")
    # Locate the Invocation section.
    inv_idx = text.find("## Invocation")
    assert inv_idx >= 0, "SKILL.md missing '## Invocation' section"
    inv_section = text[inv_idx:]
    # First fenced block after the heading.
    first_block_match = _FENCE.search(inv_section)
    assert first_block_match, "no fenced code block found in Invocation section"
    leader = _first_nonblank_line(first_block_match.group(1))
    assert leader.startswith("claude-code-review"), (
        f"Invocation section's primary block must lead with 'claude-code-review'; "
        f"got {leader!r}"
    )


def test_no_primary_module_invocations_in_examples() -> None:
    """Every fenced code block's first non-blank line must NOT use the
    `python -m code_review.cli` form. A later line in the same block is allowed
    (e.g., a comment noting both forms exist), and prose paragraphs outside code
    blocks are allowed."""
    offenders: list[str] = []
    for block in _code_blocks():
        leader = _first_nonblank_line(block)
        if leader.startswith("python -m code_review.cli"):
            offenders.append(leader)
    assert not offenders, (
        f"these fenced blocks still lead with the module form: {offenders}"
    )


def test_developer_note_present() -> None:
    """A prose paragraph (outside code blocks) must acknowledge the module-form
    fallback for source checkouts."""
    text = SKILL_MD.read_text(encoding="utf-8")
    # Strip fenced code blocks to leave only prose.
    prose = _FENCE.sub("", text)
    assert "python -m code_review.cli" in prose, (
        "expected a prose mention of `python -m code_review.cli` as the "
        "source-checkout fallback; none found"
    )
    # Must be near a context word that explains it's a fallback, not the primary.
    needle_idx = prose.find("python -m code_review.cli")
    assert needle_idx >= 0
    window = prose[max(0, needle_idx - 200) : needle_idx + 200].lower()
    context_words = ("source checkout", "developer", "dev mode", "dev install")
    assert any(w in window for w in context_words), (
        f"prose mention of module form lacks a fallback-context word "
        f"(any of {context_words}); window: {window!r}"
    )
