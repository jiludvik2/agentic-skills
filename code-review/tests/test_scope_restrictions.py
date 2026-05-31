from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from code_review.capture import CaptureOutput
from code_review.cli import app
from code_review.config import Config
from code_review.contracts import ReviewRequest

runner = CliRunner()


# A generic story-level-only stub. The scope-restriction mechanism is analyzer-agnostic;
# after ADR-0021 removed Schemathesis (the only real story-level-only adapter) we exercise
# the mechanism with a synthetic adapter rather than naming a deleted one.
class _StoryLevelOnlyAdapter:
    name: ClassVar[str] = "storyonly"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset({"story-level"})
    required_binary: ClassVar[None] = None

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        return CaptureOutput(tool="storyonly", status="ok", command=("storyonly",))


class _StubBanditAdapter:
    name: ClassVar[str] = "bandit"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[None] = None

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        return CaptureOutput(tool="bandit", status="ok", command=("bandit",))


_STUB_REGISTRY: dict[str, type[Any]] = {
    "storyonly": _StoryLevelOnlyAdapter,
    "bandit": _StubBanditAdapter,
}


def test_scope_per_task_rejects_story_level_only_analyzer() -> None:
    with (
        patch("code_review.cli.load_config", return_value=Config()),
        patch("code_review.adapters.REGISTRY", _STUB_REGISTRY),
        patch("code_review.cli.REGISTRY", _STUB_REGISTRY, create=True),
    ):
        result = runner.invoke(
            app,
            ["run", "--analyzer", "storyonly", "--scope", "per-task"],
            catch_exceptions=False,
        )
    assert result.exit_code != 0
    assert "story-level" in result.output


def test_scope_story_level_accepts_story_level_only_analyzer() -> None:
    with (
        patch("code_review.cli.load_config", return_value=Config()),
        patch("code_review.adapters.REGISTRY", _STUB_REGISTRY),
        patch("code_review.cli.REGISTRY", _STUB_REGISTRY, create=True),
    ):
        result = runner.invoke(
            app,
            ["run", "--analyzer", "storyonly", "--scope", "story-level"],
            catch_exceptions=False,
        )
    assert result.exit_code == 0


@pytest.mark.parametrize("scope", ["per-task", "story-level"])
def test_unrestricted_analyzer_accepted_at_any_scope(scope: str) -> None:
    with (
        patch("code_review.cli.load_config", return_value=Config()),
        patch("code_review.adapters.REGISTRY", _STUB_REGISTRY),
        patch("code_review.cli.REGISTRY", _STUB_REGISTRY, create=True),
    ):
        result = runner.invoke(
            app,
            ["run", "--analyzer", "bandit", "--scope", scope],
            catch_exceptions=False,
        )
    assert result.exit_code == 0
