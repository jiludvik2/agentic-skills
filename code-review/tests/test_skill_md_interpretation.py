"""s2-t3: SKILL.md must contain an 'Interpreting the bundle' section covering every
registered analyzer, the ADR-0019 status semantics, and the G2/G7 FP notes."""
from __future__ import annotations

from pathlib import Path

from code_review.adapters import REGISTRY

SKILL_MD = (
    Path(__file__).parent.parent
    / ".claude" / "skills" / "code-review" / "SKILL.md"
)

_HEADING = "## Interpreting the bundle"


def _interpretation_section() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    idx = text.find(_HEADING)
    if idx < 0:
        return ""
    # Everything from the heading to the next ## heading (or end of file)
    remainder = text[idx:]
    next_heading = remainder.find("\n## ", len(_HEADING))
    return remainder if next_heading < 0 else remainder[:next_heading]


def test_interpretation_section_present() -> None:
    """The '## Interpreting the bundle' heading must exist in SKILL.md."""
    text = SKILL_MD.read_text(encoding="utf-8")
    assert _HEADING in text, (
        f"SKILL.md is missing the '{_HEADING}' section"
    )


def test_every_analyzer_documented() -> None:
    """Every key in REGISTRY must be mentioned in the interpretation section."""
    section = _interpretation_section()
    assert section, f"'{_HEADING}' section not found or empty"
    missing = [name for name in REGISTRY if name not in section]
    assert not missing, (
        f"These registry analyzers are absent from '{_HEADING}': {missing}"
    )


def test_status_semantics_documented() -> None:
    """The section must explain all three non-ok statuses and their meaning."""
    section = _interpretation_section()
    assert section, f"'{_HEADING}' section not found or empty"
    # All three non-ok statuses must appear
    for status in ("unavailable", "error", "timeout"):
        assert status in section, (
            f"Status '{status}' not documented in '{_HEADING}'"
        )
    # 'unavailable' must NOT be treated as all-clear — the spec requires a caution
    lower = section.lower()
    caution_phrases = ("not clean", "not a finding", "not all-clear", "not installed",
                       "nothing to scan", "isn't installed", "is not")
    assert any(p in lower for p in caution_phrases), (
        f"'{_HEADING}' must clarify that 'unavailable' ≠ clean; "
        f"expected one of {caution_phrases} near 'unavailable'"
    )


def test_fp_notes_present() -> None:
    """The section must include false-positive / confidence caveats for vulture and knip."""
    section = _interpretation_section()
    assert section, f"'{_HEADING}' section not found or empty"
    lower = section.lower()

    fp_phrases = ("false positive", "false-positive", "fp", "confidence")
    for tool in ("vulture", "knip"):
        # Find the tool mention, then check for an FP/confidence word nearby
        idx = lower.find(tool)
        assert idx >= 0, f"'{tool}' not found in '{_HEADING}' section"
        window = lower[max(0, idx - 100): idx + 300]
        assert any(p in window for p in fp_phrases), (
            f"No false-positive/confidence caveat near '{tool}' in '{_HEADING}'; "
            f"window: {window!r}"
        )
