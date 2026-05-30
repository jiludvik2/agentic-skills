---
id: s1-t1c-migrate-schemathesis
kind: task
project: code-review
status: active
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md, s1-migrate-adapters-and-emit-bundle.md]
created: 2026-05-30
updated: 2026-05-30
tags: [migration, adapters, schemathesis, subprocess, contract-testing, high-risk]
---

# Task s1-t1c — migrate schemathesis (library → subprocess; auth/sandbox design)

## Outcome

The schemathesis adapter (the largest, ~10K, currently running the library **in-process**)
becomes a thin subprocess invocation of the `schemathesis` console script that returns a raw
`CaptureOutput` via `run_and_capture`, preserving the existing **auth-header injection**,
**sandbox/network isolation**, and **`story-level` scope restriction**. All in-process schema
loading, per-operation iteration, SARIF building, and `final_status` derivation are deleted.

## Why this is its own task (autonomy-gate fork)

Unlike the other adapters, schemathesis has no subprocess to "keep" and its in-process logic
carries behaviour the spec does not dictate how to reproduce under a subprocess:
- **auth** — currently injected into in-process schema calls; under a subprocess it must pass
  through `schemathesis run` flags (e.g. `-H "Authorization: …"`) or env.
- **sandbox isolation** — the in-process run is contained; a subprocess that performs live
  HTTP to the target must stay within the same isolation guarantees (no unintended egress).
- **scope** — `scope_restrictions` already pins this adapter to `story-level`; preserve it.

**Execution starts by reading the current `adapters/schemathesis_.py` in full** to extract
the exact auth/sandbox/scope behaviour, then maps each to a `schemathesis run` invocation.
**If the auth-or-sandbox-under-subprocess mapping cannot be made faithfully** (e.g. a
behaviour has no CLI equivalent), **halt via the autonomy-gate escalation interface** rather
than inventing semantics — this is the explicitly-flagged design fork.

## Design (high level — refine against the current adapter at execution)

`run()` becomes: scope guard (`story-level`) → availability pre-flight (console script +
schema reachable) → build the `schemathesis run <schema> -H <auth> …` argv preserving
isolation → `run_and_capture(...)` → return the raw capture verbatim. Delete the in-process
`get_all_operations` loop, the per-op SARIF result building, and the `final_status` mapping
(status now comes from `run_and_capture`'s exit-code classification; timeout handled by the
primitive).

## Acceptance criteria

- schemathesis returns a `CaptureOutput`; no in-process schema iteration / SARIF builder /
  `final_status` logic remains (`grep` clean).
- The built argv **pins the auth-header injection and the isolation invocation** by test, and
  the `story-level` scope restriction is preserved (scope-guard test).
- Raw-capture test: known stdout verbatim, status `ok` on tolerated exit; availability test:
  pre-flight failure → `unavailable`/`error`, no exception.
- One `integration`-marked real run against a local fixture API asserting a non-empty raw
  capture (analyzer-coverage discipline). Mark/skip appropriately if it needs a live server.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.
- **Auth/sandbox-under-subprocess disposition recorded** in close notes (how each mapped, or
  the operator decision if the gate escalated).

## Test specification (write first, confirm RED)

Rewrite `tests/test_adapters/test_schemathesis.py` (and any schemathesis SARIF test):

1. `test_schemathesis_invocation_pins_auth_and_isolation` — patch `run_and_capture`, assert
   the argv/env carries the auth header(s) and the isolation invocation.
2. `test_schemathesis_scope_restriction` — non-`story-level` scope → not run / guarded.
3. `test_schemathesis_captures_raw_stdout` — patched primitive → verbatim stdout, status `ok`.
4. `test_schemathesis_unavailable_preflight` — pre-flight failure → no exception.
5. Delete the old in-process/SARIF assertions (don't adapt).

## Notes

- Highest-risk migration in the story; do it alone, after s1-t1 and s1-t1b are green.
- If `schemathesis run` cannot reproduce a needed auth/sandbox behaviour, escalate — do not
  silently weaken auth or isolation to fit the subprocess model.
