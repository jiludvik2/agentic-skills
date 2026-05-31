from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from code_review.config import ConfigError, load_config

# The thin-runner CLI (ADR-0020) emits raw per-tool captures, so the former
# SARIF-normalisation knobs (dedup tolerance, severity overrides, hotspot weights) are gone.
# Config now carries only the two options that still steer invocation.


def test_absent_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "code-review.toml")
    assert config.disabled_analyzers == []
    assert config.semgrep_rules is None


def test_load_config_reads_disabled_analyzers(tmp_path: Path) -> None:
    toml = tmp_path / "code-review.toml"
    toml.write_text('disabled_analyzers = ["trivy", "pydeps"]\n')
    cfg = load_config(tmp_path / "code-review.toml")
    assert cfg.disabled_analyzers == ["trivy", "pydeps"]


def test_load_config_disabled_analyzers_default_empty(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "code-review.toml")  # no toml file
    assert cfg.disabled_analyzers == []


def test_malformed_toml_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text("this is [not valid toml !!!")
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path / "code-review.toml")
    assert str(tmp_path) in str(exc_info.value) or "code-review.toml" in str(exc_info.value)


# ---------------------------------------------------------------------------
# semgrep_rules (root-level key; ADR-0016 #5)
# ---------------------------------------------------------------------------


def test_config_parses_semgrep_rules(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            semgrep_rules = "/etc/polyreview/security.yaml"
        """)
    )
    config = load_config(tmp_path / "code-review.toml")
    assert config.semgrep_rules == "/etc/polyreview/security.yaml"


def test_semgrep_rules_absent_is_none(tmp_path: Path) -> None:
    config = load_config(tmp_path / "code-review.toml")
    assert config.semgrep_rules is None
