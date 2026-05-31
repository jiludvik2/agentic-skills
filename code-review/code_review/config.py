from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when code-review.toml cannot be parsed."""


@dataclass
class Config:
    disabled_analyzers: list[str] = field(default_factory=list)
    semgrep_rules: str | None = None


def load_config(config_path: Path | None) -> Config:
    """Parse a code-review.toml file; return defaults if `config_path` is None
    or the file is absent. The CWD lookup and precedence policy live in
    cli._resolve_config_path; the existence check here is a defensive fallback
    so direct callers (notably tests) don't need to pre-check.

    The thin-runner CLI (ADR-0020) emits raw per-tool captures, so the former
    SARIF-normalisation/ranking tunables are gone; only the two options that still
    steer invocation remain."""
    if config_path is None or not config_path.exists():
        return Config()

    try:
        raw: dict[str, Any] = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"Failed to parse {config_path}: {exc}"
        ) from exc

    disabled_analyzers: list[str] = [
        str(x) for x in raw.get("disabled_analyzers", [])
    ]

    semgrep_rules_raw = raw.get("semgrep_rules")
    semgrep_rules = str(semgrep_rules_raw) if semgrep_rules_raw is not None else None

    return Config(
        disabled_analyzers=disabled_analyzers,
        semgrep_rules=semgrep_rules,
    )
