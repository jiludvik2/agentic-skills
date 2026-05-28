from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.cli import app
from tests.conftest import FakeAnalyzer

REPO_ROOT = Path(__file__).parent.parent
CAPS = REPO_ROOT / "code_review" / "capabilities.json"


def test_capabilities_static_section_matches_file() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--capabilities"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    expected = json.loads(CAPS.read_text(encoding="utf-8"))
    assert data["static"] == expected


def test_capabilities_runtime_marks_missing_binary_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    runner = CliRunner()
    result = runner.invoke(app, ["--capabilities"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["analyzers"]["semgrep"]["status"] == "unavailable"
    assert data["analyzers"]["semgrep"]["error"]
    # radon is library-based, not gated on a PATH binary — stays available
    assert data["analyzers"]["radon"]["status"] == "available"


def test_capabilities_runtime_marks_present_binary_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/local/bin/{name}")
    runner = CliRunner()
    result = runner.invoke(app, ["--capabilities"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["analyzers"]["semgrep"]["status"] == "available"
    assert data["analyzers"]["semgrep"]["error"] is None


def test_capabilities_runtime_recomputed_each_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("shutil.which", lambda name: None)
    first = json.loads(runner.invoke(app, ["--capabilities"]).output)
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    second = json.loads(runner.invoke(app, ["--capabilities"]).output)
    assert first["analyzers"]["semgrep"]["status"] == "unavailable"
    assert second["analyzers"]["semgrep"]["status"] == "available"


def test_analyzer_registry_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "synthetic", FakeAnalyzer)
    runner = CliRunner()
    caps = json.loads(runner.invoke(app, ["--capabilities"]).output)
    assert "synthetic" in caps["analyzers"], "new registry entry not surfaced in --capabilities"
    # accepted as --analyzer without code change
    result = runner.invoke(app, ["--analyzer", "synthetic", "--target", "."])
    assert result.exit_code == 0, result.output


# --review / --depth value acceptance/rejection is covered by
# tests/test_review_selection_validation.py (the task that owns review selection).
