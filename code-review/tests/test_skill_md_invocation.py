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
    """Within every fenced code block, no NON-COMMENT line may use the
    `python -m code_review.cli` form. A `#`-prefixed comment line mentioning
    it is fine (some examples use comment headers like `# Quick security review`
    above the invocation — those headers are not the invocation themselves).
    Prose paragraphs outside code blocks are also allowed."""
    offenders: list[tuple[int, str]] = []
    for block_idx, block in enumerate(_code_blocks()):
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "python -m code_review.cli" in stripped:
                offenders.append((block_idx, stripped))
    assert not offenders, (
        f"non-comment invocations using the module form remain in these blocks: "
        f"{offenders}"
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
