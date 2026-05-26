from __future__ import annotations

import pytest

from code_review.severity import map_severity

VALID_LABELS = {"critical", "important", "minor", "nit"}

MAPPING_TABLE = [
    # (level, properties_severity, expected)
    ("error", None, "critical"),
    ("error", "critical", "critical"),
    ("error", "nit", "critical"),  # level takes precedence over low properties_severity
    ("warning", "important", "important"),
    ("warning", "high", "important"),
    ("warning", None, "minor"),
    ("warning", "medium", "minor"),  # unrecognised → fallback
    ("note", None, "nit"),
    ("note", "info", "nit"),
    ("none", None, "nit"),
    # boundary: warning+critical — properties_severity "critical" wins per first OR-rule
    ("warning", "critical", "critical"),
    # unknown level + non-critical props → nit (unknown level treated as none)
    ("fatal", "high", "nit"),
    # unknown level + critical props → critical (OR-rule fires first)
    ("fatal", "critical", "critical"),
]


@pytest.mark.parametrize("level,props_sev,expected", MAPPING_TABLE)
def test_map_severity_table(level: str, props_sev: str | None, expected: str) -> None:
    assert map_severity(level, props_sev) == expected


def test_map_severity_unknown_strings_never_raise() -> None:
    unknown_pairs = [
        ("bogus", "bogus"),
        ("", ""),
        ("ERROR", "CRITICAL"),
        ("Warning", None),
        (None, None),  # type: ignore[arg-type]
        ("note", "UNKNOWN"),
        ("undefined", "medium"),
        ("debug", None),
        ("fatal", "critical"),
        ("info", "high"),
    ]
    for level, props_sev in unknown_pairs:
        result = map_severity(level, props_sev)  # type: ignore[arg-type]
        assert result in VALID_LABELS, (
            f"map_severity({level!r}, {props_sev!r}) returned {result!r}, "
            f"expected one of {VALID_LABELS}"
        )
