"""End-to-end CLI facade tests using CliRunner (in-process, no real tools)."""
import json

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.cli import app
from tests.conftest import FakeAnalyzer


def test_fake_adapter_no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []

    def _raise(*args: object, **kwargs: object) -> object:
        called.append(True)
        raise AssertionError("subprocess spawned")

    monkeypatch.setattr("asyncio.create_subprocess_exec", _raise)
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)

    runner = CliRunner()
    result = runner.invoke(app, ["run", "--analyzer", "fake", "--target", "."])

    assert not called, "FakeAnalyzer must not spawn any subprocess"
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "fake" in {o["tool"] for o in data["outputs"]}


def test_fake_adapter_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)

    runner = CliRunner()
    result = runner.invoke(app, ["run", "--analyzer", "fake", "--target", "."])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "outputs" in data
    assert "fake" in {o["tool"] for o in data["outputs"]}
