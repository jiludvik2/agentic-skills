from __future__ import annotations

_SDLC_SEVERITY_BY_LEVEL: dict[str, str] = {
    "error": "critical",
    "warning": "minor",
    "note": "nit",
    "none": "nit",
}

_SDLC_SEVERITY_BY_PROPS: dict[str, str] = {
    "critical": "critical",
    "important": "important",
    "high": "important",
    "medium": "minor",
    "low": "minor",
    "nit": "nit",
    "info": "nit",
}


def map_severity(level: str, properties_severity: str | None) -> str:
    """Map SARIF level + properties.severity to the SDLC taxonomy label.

    Rules (applied in order):
      1. level==error  → critical
      2. properties_severity==critical  → critical
      3. level==warning AND properties_severity in {important, high}  → important
      4. level==note or level==none  → nit
      5. everything else  → minor (includes unknown levels)
    """
    norm_level = (level or "").lower()
    norm_props = (properties_severity or "").lower()

    if norm_level == "error":
        return "critical"

    if norm_props == "critical":
        return "critical"

    if norm_level == "warning":
        return _SDLC_SEVERITY_BY_PROPS.get(norm_props, "minor") if norm_props else "minor"

    if norm_level in ("note", "none"):
        return "nit"

    return _SDLC_SEVERITY_BY_PROPS.get(norm_props, "nit")
