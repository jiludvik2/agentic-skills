---
id: s1-t0-type-consolidation-and-status-sot
kind: task
project: code-review
status: active
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md, s0-contract-inversion-and-bundle.md]
created: 2026-05-30
updated: 2026-05-30
tags: [contract, capture, status, refactor]
---

# Task s1-t0 — type consolidation + ADR-0019 status single-source-of-truth

## Outcome

One raw-capture return type for adapters and one shared definition of the ADR-0019 status
taxonomy — the foundation the adapter migrations (s1-t1/t2) and CLI switch (s1-t3) build
on. Resolves s0 story-level Minor #1 (three disconnected copies of the status values).

## Design

1. **Status SoT.** Promote the ADR-0019 taxonomy to a single shared definition — a
   `StrEnum` (or `Literal` + frozenset) in one module (candidate: `code_review/contracts.py`
   or a small `code_review/status.py`). `capture.py` references it (replacing the private
   `_OK/_ERROR/_TIMEOUT/_UNAVAILABLE` constants); `review_bundle.py` references it; add a
   test asserting the schema enum in `review-bundle.v1.json` equals the shared set
   (closes the drift the s0 review flagged).
2. **Adapter return type.** Decide and execute the consolidation of `CaptureOutput` (s0,
   `capture.py`) with the legacy `AnalyzerOutput` (`contracts.py`, still carrying
   `sarif`/`metrics`). Recommended: adapters return `CaptureOutput`; the legacy
   `AnalyzerOutput`/`MetricSet` are deleted in s1-t3 once no adapter and no CLI path
   references them. The optional rename `CaptureOutput → AnalyzerOutput` (deferred from s0)
   is the implementer's call — if renamed, do it here in one move before the adapter
   migrations import it widely. Update the `Analyzer` protocol's `run()` return annotation.
3. **No adapter bodies migrate in this task** — only the shared type/enum surface and the
   protocol. Adapters still compile against the old path until s1-t1/t2 (keep the suite
   green: if the protocol return type changes, adapters may need a transitional shim — keep
   it minimal and delete it in s1-t1/t2).

## Acceptance criteria

- A single shared ADR-0019 status definition exists; `capture.py` and `review_bundle.py`
  both reference it; the private status constants in `capture.py` are gone.
- A test asserts the published schema's status enum equals the shared definition (so the
  schema and code cannot silently drift).
- The adapter return type is consolidated to one type; the `Analyzer` protocol's `run()`
  annotation matches; `grep` shows the chosen type is what adapters will return.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean; the full suite
  stays green (any transitional shim is covered or trivially safe).

## Test specification (write first, confirm RED)

`tests/test_status_sot.py` (new) + edits to `tests/test_capture.py` / `tests/test_review_bundle.py`:

1. `test_status_values_are_adr0019` — the shared definition contains exactly
   `{ok, error, timeout, unavailable}` and nothing else.
2. `test_schema_enum_matches_status_sot` — load `review-bundle.v1.json`; its
   `outputs.items.properties.status.enum` equals the shared set (sorted compare).
3. `test_capture_uses_shared_status` — `CaptureOutput(...).status` and
   `CaptureOutput.unavailable(...).status` are members of the shared definition (guards the
   constant removal).
4. Adjust any existing test that imported the private `_OK`-style constants (there should
   be none outside `capture.py`; confirm by grep).

## Notes

- Keep this task **surgical** — it is the type/enum seam only. The big deletions and the
  adapter rewrites are s1-t1/t2/t3. A clean s1-t0 makes those three mechanical.
- If renaming `CaptureOutput → AnalyzerOutput`, the legacy `AnalyzerOutput` must be gone or
  shimmed in the same task to avoid a name clash — simplest is to keep the name
  `CaptureOutput` through s1 and delete legacy `AnalyzerOutput` in s1-t3.
