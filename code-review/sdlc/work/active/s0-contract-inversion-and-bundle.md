---
id: s0-contract-inversion-and-bundle
kind: story
project: code-review
status: active
parent: epic-analyzer-thin-runner
children:
  - s0-t0-capture-contract-and-primitive
  - s0-t1-review-bundle-and-schema
sources: [epic-analyzer-thin-runner.md, adr-0020-thin-invocation-runner.md]
created: 2026-05-30
updated: 2026-05-30
tags: [contract, bundle, capture, runner]
---

# Story s0 — contract inversion + bundle format

Governed by **ADR-0020**. First story of `epic-analyzer-thin-runner`.

## Why

The redesign replaces per-tool SARIF normalisation with raw capture + agent
interpretation. Before any adapter can be migrated (s1), the **new contract** must
exist: a raw-capture output type, a primitive that runs a tool and classifies its
outcome into the ADR-0019 status taxonomy, and a bundle type the CLI will emit and the
agent will read.

## Strangle, not big-bang

s0 is **purely additive**. It introduces the new types and primitive **alongside** the
existing SARIF path — nothing is rewired, nothing is deleted. The live CLI still emits
SARIF after s0. This keeps the entire existing test suite green. The switch onto the new
rail and the deletion of the normalisation layer (`_to_sarif`, `aggregator`, `severity`,
`hotspots`, `MetricSet`) happen in **s1**.

## Scope

1. **`CaptureOutput`** — a frozen raw-capture contract: `tool`, `stdout`, `stderr`,
   `exit_code`, `status` (ok | error | timeout | unavailable — ADR-0019), `error`,
   `command`, `duration_s`. Plus an `unavailable(tool, reason)` constructor (replacing the
   `empty_sarif`-based unavailable pattern).
2. **`run_and_capture`** — a primitive wrapping `base.run_subprocess` that returns a
   `CaptureOutput`, mapping execution outcomes to status: clean/tolerated exit → `ok`,
   untolerated exit → `error`, timeout → `timeout`, spawn failure → `error`. Preserves raw
   stdout/stderr **verbatim** (no parsing). `unavailable` is an adapter pre-flight decision
   (s1), represented by the type but not produced by this primitive.
3. **`ReviewBundle`** — aggregates the `ReviewRequest` echo (domain/depth/target/diff/
   languages) + a tuple of `CaptureOutput`; serialises to stable JSON; validates against a
   **published bundle JSON schema** (the agent's contract, analogous to the old SARIF
   schema).

## Acceptance criteria

- A `CaptureOutput` frozen dataclass exists with the fields above; `status` is constrained
  to the ADR-0019 taxonomy; an `unavailable(tool, reason)` constructor returns a
  `status="unavailable"` capture with empty stdout and the reason in `error`.
- `run_and_capture` returns `ok` (with verbatim stdout) on tolerated exit codes, `error`
  on untolerated exit (with stderr in `error`), `timeout` on timeout, and `error` on spawn
  failure — never raises, never parses output.
- A `ReviewBundle` serialises to deterministic JSON carrying the request metadata and one
  entry per capture (tool, status, exit_code, stdout, stderr, error, command); it round-
  trips; it validates against the published schema; an invalid bundle fails validation.
- **No regression:** the existing SARIF path, adapters, and their tests remain unchanged
  and green. s0 adds code; it removes none.
- `uv run pytest`, `uv run ruff check .`, and `uv run mypy` are all clean.

## Deferred (BDD-deferral annotations)

These belong to later stories and are **out of scope for s0** — the verifier should not
flag them missing:

- Adapter migration to `run_and_capture` / `CaptureOutput` — **s1**.
- Deletion of `_to_sarif` (×~8), `aggregator.py`, `severity.py`, `hotspots.py`,
  `MetricSet`, SARIF builders in `sarif_utils.py` — **s1**.
- CLI emitting the bundle instead of SARIF; SKILL.md interpretation guidance — **s2**.
- jscpd scope (G1), vulture/knip FP handling (G2/G7) — **s1/s2**.
- Optional rename `CaptureOutput` → `AnalyzerOutput` once the old type is deleted — **s1**.

## Tasks

- **s0-t0** — `CaptureOutput` contract + `run_and_capture` primitive (+ `unavailable`
  constructor).
- **s0-t1** — `ReviewBundle` type + JSON serialisation + published bundle schema.
