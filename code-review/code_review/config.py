from __future__ import annotations

import importlib.resources
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_DEDUP_TOLERANCE = 3
_DEFAULT_HOTSPOT_WEIGHTS = {
    "severity_weighted_findings": 1.0,
    "cyclomatic_complexity": 0.5,
    "coupling": 0.3,
}


class ConfigError(Exception):
    """Raised when code-review.toml cannot be parsed."""


def _load_caps_weights() -> dict[str, float]:
    caps_path = importlib.resources.files("code_review").joinpath("capabilities.json")
    if not caps_path.is_file():
        return dict(_DEFAULT_HOTSPOT_WEIGHTS)
    caps = json.loads(caps_path.read_text(encoding="utf-8"))
    raw = caps.get("hotspots", {}).get("weights", _DEFAULT_HOTSPOT_WEIGHTS)
    return {k: float(v) for k, v in raw.items()}


_VALID_SDLC_LABELS = frozenset({"critical", "important", "minor", "nit"})


@dataclass
class Config:
    dedup_line_tolerance: int = _DEFAULT_DEDUP_TOLERANCE
    severity_overrides: dict[str, str] = field(default_factory=dict)
    hotspot_weights: dict[str, float] = field(default_factory=_load_caps_weights)
    disabled_analyzers: list[str] = field(default_factory=list)
    contract_testing: dict[str, Any] = field(default_factory=dict)
    semgrep_rules: str | None = None


def load_config(config_path: Path | None) -> Config:
    """Parse a code-review.toml file; return defaults if `config_path` is None
    or the file is absent. The CWD lookup and precedence policy live in
    cli._resolve_config_path; the existence check here is a defensive fallback
    so direct callers (notably tests) don't need to pre-check."""
    if config_path is None or not config_path.exists():
        return Config(hotspot_weights=_load_caps_weights())

    try:
        raw: dict[str, Any] = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"Failed to parse {config_path}: {exc}"
        ) from exc

    dedup_tolerance = int(raw.get("dedup", {}).get("line_tolerance", _DEFAULT_DEDUP_TOLERANCE))
    severity_overrides: dict[str, str] = {
        str(k): str(v) for k, v in raw.get("severity", {}).items()
    }
    for rule_id, label in severity_overrides.items():
        if label not in _VALID_SDLC_LABELS:
            raise ConfigError(
                f"Invalid severity override for '{rule_id}': '{label}' is not one of "
                f"{sorted(_VALID_SDLC_LABELS)}"
            )

    base_weights = _load_caps_weights()
    toml_weights: dict[str, Any] = raw.get("hotspots", {}).get("weights", {})
    hotspot_weights = {**base_weights, **{k: float(v) for k, v in toml_weights.items()}}

    disabled_analyzers: list[str] = [
        str(x) for x in raw.get("disabled_analyzers", [])
    ]

    contract_testing: dict[str, Any] = dict(
        raw.get("contract_testing", {}).get("targets", {})
    )

    semgrep_rules_raw = raw.get("semgrep_rules")
    semgrep_rules = str(semgrep_rules_raw) if semgrep_rules_raw is not None else None

    return Config(
        dedup_line_tolerance=dedup_tolerance,
        severity_overrides=severity_overrides,
        hotspot_weights=hotspot_weights,
        disabled_analyzers=disabled_analyzers,
        contract_testing=contract_testing,
        semgrep_rules=semgrep_rules,
    )
