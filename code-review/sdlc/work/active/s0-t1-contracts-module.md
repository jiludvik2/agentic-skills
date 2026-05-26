---
id: s0-t1-contracts-module
kind: task
project: code-review
status: active
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t1 — Contracts module

## Outcome

`code_review/contracts.py` defines the `Analyzer` Protocol, `AnalyzerOutput`, `MetricSet`, and `ReviewRequest` exactly as specified in architecture §4. This is the seam every adapter and the CLI depends on; nothing else in s0 can be written until this passes.

## Acceptance Criteria

- `from code_review.contracts import Analyzer, AnalyzerOutput, MetricSet, ReviewRequest` succeeds.
- `Analyzer` is a `typing.runtime_checkable` `Protocol` with: `name: str`, `kind: str`, `default_timeout_s: int`, `scope_restrictions: frozenset[str]`, and `async def run(self, request: ReviewRequest) -> AnalyzerOutput`.
- `AnalyzerOutput` is a `@dataclass(frozen=True)` with: `sarif: dict`, `metrics: Optional[MetricSet] = None`, `duration_s: float = 0.0`, `status: str = "ok"`, `error: Optional[str] = None`, `raw_output_path: Optional[str] = None`.
- `MetricSet` is a `@dataclass(frozen=True)` with: `per_file: dict[str, dict]`, `per_class: dict[str, dict]`, `coupling: dict[str, dict]`.
- `ReviewRequest` is a `@dataclass(frozen=True)` with: `scope: str`, `diff_range: Optional[str]`, `target_paths: tuple[str, ...]`, `languages: frozenset[str]`, `config: dict`.
- A class missing `async def run` returns `False` from `isinstance(obj, Analyzer)`.
- `mypy --strict` passes on `contracts.py` with zero errors.

## Test specification

`tests/test_contracts.py` — written first, all fail with `ImportError`, then pass:

- `test_protocol_members_present` — use `inspect.getmembers` and `typing.get_type_hints` to assert `name`, `kind`, `default_timeout_s`, `scope_restrictions`, and `run` exist on `Analyzer`; assert `run` is a coroutine function.
- `test_analyzer_output_is_frozen_dataclass` — `dataclasses.is_dataclass(AnalyzerOutput)` is True; construct a minimal instance; assert mutating any field raises `FrozenInstanceError`.
- `test_metric_set_fields` — construct `MetricSet(per_file={}, per_class={}, coupling={})` and assert all three attributes are accessible.
- `test_review_request_target_paths_is_tuple` — construct a `ReviewRequest`; assert `isinstance(req.target_paths, tuple)`.
- `test_non_conforming_class_fails_protocol` — define `class Bad: pass`; assert `isinstance(Bad(), Analyzer)` is `False`.
