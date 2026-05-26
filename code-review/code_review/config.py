from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SKILL_DIR = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "code-review"

_DEFAULT_DEDUP_TOLERANCE = 3
_DEFAULT_HOTSPOT_WEIGHTS = {
    "severity_weighted_findings": 1.0,
    "cyclomatic_complexity": 0.5,
    "coupling": 0.3,
}


class ConfigError(Exception):
    """Raised when code-review.toml cannot be parsed."""


def _load_caps_weights() -> dict[str, float]:
    caps_path = _SKILL_DIR / "capabilities.json"
    if not caps_path.exists():
        return dict(_DEFAULT_HOTSPOT_WEIGHTS)
    caps = json.loads(caps_path.read_text(encoding="utf-8"))
    raw = caps.get("hotspots", {}).get("weights", _DEFAULT_HOTSPOT_WEIGHTS)
    return {k: float(v) for k, v in raw.items()}


@dataclass
class Config:
    dedup_line_tolerance: int = _DEFAULT_DEDUP_TOLERANCE
    severity_overrides: dict[str, str] = field(default_factory=dict)
    hotspot_weights: dict[str, float] = field(default_factory=_load_caps_weights)


def load_config(skill_dir: Path) -> Config:
    """Load code-review.toml from skill_dir; return defaults if absent."""
    toml_path = skill_dir / "code-review.toml"
    if not toml_path.exists():
        return Config(hotspot_weights=_load_caps_weights())

    try:
        raw: dict[str, Any] = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"Failed to parse {toml_path}: {exc}"
        ) from exc

    dedup_tolerance = int(raw.get("dedup", {}).get("line_tolerance", _DEFAULT_DEDUP_TOLERANCE))
    severity_overrides: dict[str, str] = {
        str(k): str(v) for k, v in raw.get("severity", {}).items()
    }

    base_weights = _load_caps_weights()
    toml_weights: dict[str, Any] = raw.get("hotspots", {}).get("weights", {})
    hotspot_weights = {**base_weights, **{k: float(v) for k, v in toml_weights.items()}}

    return Config(
        dedup_line_tolerance=dedup_tolerance,
        severity_overrides=severity_overrides,
        hotspot_weights=hotspot_weights,
    )
