from __future__ import annotations

_PYTHON_ADAPTERS = frozenset({"bandit", "vulture", "pydeps", "cohesion", "radon", "semgrep"})
_JS_ADAPTERS = frozenset({"eslint", "jscpd", "knip", "depcruiser"})
_COMMON_ADAPTERS = frozenset({"gitleaks", "trivy"})


def select_adapters(languages: frozenset[str]) -> list[str]:
    """Return the default adapter list for the given language set."""
    selected: set[str] = set(_COMMON_ADAPTERS)
    if "python" in languages:
        selected |= _PYTHON_ADAPTERS
    if "javascript" in languages or "typescript" in languages:
        selected |= _JS_ADAPTERS
    return sorted(selected)
