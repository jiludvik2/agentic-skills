"""CWD-relative code-review.toml lookup and --config flag override.

Per s0-t2: cli._resolve_config_path resolves the config-file path from the
--config arg (if given) or CWD (if no flag). load_config takes the resolved
Path | None directly — it no longer walks any skill-dir."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from code_review.cli import _resolve_config_path, app
from code_review.config import load_config

runner = CliRunner()


def _write_toml(path: Path, marker: int) -> None:
    # The value is arbitrary; resolution tests only care about *which* file is found, and
    # the load_config tests below read semgrep_rules back. (`marker` distinguishes files.)
    path.write_text(f'semgrep_rules = "/rules/{marker}.yaml"\n')


# --- _resolve_config_path: pure resolution logic --------------------------


def test_resolve_none_with_cwd_toml_returns_cwd_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cwd_toml = tmp_path / "code-review.toml"
    _write_toml(cwd_toml, 5)
    assert _resolve_config_path(None) == cwd_toml


def test_resolve_none_with_no_cwd_toml_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _resolve_config_path(None) is None


def test_resolve_explicit_existing_returns_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    explicit = tmp_path / "elsewhere" / "code-review.toml"
    explicit.parent.mkdir()
    _write_toml(explicit, 7)
    assert _resolve_config_path(explicit) == explicit


def test_resolve_explicit_missing_raises_with_path_in_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "nope.toml"
    with pytest.raises(FileNotFoundError, match=str(missing)):
        _resolve_config_path(missing)


def test_resolve_explicit_wins_over_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cwd_toml = tmp_path / "code-review.toml"
    _write_toml(cwd_toml, 5)
    explicit = tmp_path / "other.toml"
    _write_toml(explicit, 9)
    assert _resolve_config_path(explicit) == explicit


# --- load_config: file-path semantics -------------------------------------


def test_load_config_none_returns_defaults() -> None:
    config = load_config(None)
    assert config.disabled_analyzers == []
    assert config.semgrep_rules is None


def test_load_config_reads_explicit_path(tmp_path: Path) -> None:
    toml = tmp_path / "code-review.toml"
    _write_toml(toml, 5)
    config = load_config(toml)
    assert config.semgrep_rules == "/rules/5.yaml"


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    """load_config trusts its caller; if the file doesn't exist it returns
    defaults. Existence checking lives in _resolve_config_path."""
    config = load_config(tmp_path / "missing.toml")
    assert config.semgrep_rules is None


# --- CLI integration: --config flag wiring --------------------------------


def test_cli_config_missing_exits_nonzero_with_path(tmp_path: Path) -> None:
    missing = tmp_path / "definitely-not-here.toml"
    result = runner.invoke(
        app, ["run", "--config", str(missing), "--review", "security"]
    )
    assert result.exit_code != 0
    assert str(missing) in (result.stderr or result.stdout)


def test_cli_capabilities_works_without_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--capabilities should not require a config file even when CWD has none."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["run", "--capabilities"])
    assert result.exit_code == 0, result.stderr or result.stdout
