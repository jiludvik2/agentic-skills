from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class Analyzer(Protocol):
    name: str
    kind: str
    default_timeout_s: int
    scope_restrictions: frozenset[str]

    async def run(self, request: ReviewRequest) -> AnalyzerOutput: ...


@dataclass(frozen=True)
class MetricSet:
    per_file: dict[str, dict[str, Any]]
    per_class: dict[str, dict[str, Any]]
    coupling: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class AnalyzerOutput:
    sarif: dict[str, Any]
    metrics: Optional[MetricSet] = None
    duration_s: float = 0.0
    status: str = "ok"
    error: Optional[str] = None
    raw_output_path: Optional[str] = None


@dataclass(frozen=True)
class ReviewRequest:
    scope: str
    diff_range: Optional[str]
    target_paths: tuple[str, ...]
    languages: frozenset[str]
    config: dict[str, Any]
