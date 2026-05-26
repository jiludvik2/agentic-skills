"""Shared test doubles for code_review tests."""
from __future__ import annotations

import asyncio
from typing import ClassVar

from code_review.contracts import AnalyzerOutput, ReviewRequest


class FakeAnalyzer:
    name: ClassVar[str] = "fake"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        return AnalyzerOutput(sarif={}, status="ok")


class FakeAnalyzer2(FakeAnalyzer):
    name = "fake2"


class SlowFakeAnalyzer:
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    sleep_s: ClassVar[float] = 0.0
    name: ClassVar[str] = "slow"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        await asyncio.sleep(self.sleep_s)
        return AnalyzerOutput(sarif={}, status="ok")
