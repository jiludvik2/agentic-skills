---
id: s1-t2-migrate-js-adapters
kind: task
project: code-review
status: active
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md, post-coverage-eval-findings.md]
created: 2026-05-30
updated: 2026-05-30
tags: [migration, adapters, javascript, capture, g1]
---

# Task s1-t2 — migrate the 4 JS adapters + fold in G1 (jscpd scope)

## Outcome

The 4 JS adapters invoke their vendored tools with the same argv/cwd/`NODE_PATH` as today
and return raw `CaptureOutput`s, preserving the `js_base` availability probe. The jscpd
language-scope question (G1) is settled at the invocation layer.

## Design

Same invoke-and-capture pattern as s1-t1, but the JS pre-flight is `js_base`'s
`probe_js_adapter` / `js_unavailable` (vendored `node_modules` presence). Replace
`js_unavailable(...)` returns with `CaptureOutput.unavailable(name, reason)`.

Adapters (load-bearing invocation detail to PRESERVE and pin by test):

- **eslint** — **`NODE_PATH` + cwd anchoring** for flat-config discovery (F8 — eslint must
  run anchored at the config dir); sonarjs plugin. Delete the SARIF-formatter handling
  (raw capture instead).
- **depcruiser** — needs the vendored **typescript 5.x** transpiler to enumerate `.ts/.tsx`
  in a directory target; empirical Node floor 16.10.2 (`node:fs/constants`). Preserve the
  directory-target invocation. Delete `_depcruiser_to_sarif`.
- **jscpd** — **G1 fold-in**: jscpd is deliberately JS-scoped by product design
  (`lang_select._JS_ADAPTERS`), but on real apps it scanned HTML/non-JS (scope leak via the
  invocation `--format`/path args, not the selector). Settle the intended scope here: pin
  the invocation's `--format`/glob so it covers the intended JS/TS set and nothing else,
  and assert it. Delete `_jscpd_to_sarif`.
- **knip** — unused-export detection; delete `_knip_to_sarif`. (G7 knip false-positives are
  agent-interpretation, deferred to s2 — do NOT add FP-filtering here.)

## Acceptance criteria

- All 4 JS adapters return a `CaptureOutput`; no `_to_sarif` remains in the JS set.
- `eslint` invocation test pins `NODE_PATH` + the cwd anchor; `depcruiser` test pins the
  TS-aware directory invocation; `jscpd` test pins the settled `--format`/scope (G1);
  `knip` test pins its invocation.
- Availability tests use the `js_base` probe: vendored-binary-absent → `unavailable`.
- Raw-capture tests: known stdout lands verbatim, status `ok` on tolerated exit.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.
- **G1 disposition recorded** in this task's close notes: what the settled jscpd scope is
  and how the invocation enforces it.

## Test specification (write first, confirm RED)

Rewrite each `tests/test_adapters/test_<tool>.py` (eslint, depcruiser, jscpd, knip):

1. `test_<tool>_invocation_pins_flags` — assert the built argv/env contains the load-bearing
   detail (eslint `NODE_PATH`+cwd; depcruiser TS/dir; jscpd `--format`/scope; knip config).
2. `test_<tool>_captures_raw_stdout` — patched primitive feeds known stdout → verbatim on
   `CaptureOutput.stdout`, status `ok`.
3. `test_<tool>_unavailable_when_vendored_binary_absent` — `js_base` probe fails →
   `status=="unavailable"`, no exception.
4. One `integration`-marked real run per adapter on a JS fixture asserting a non-empty raw
   capture (and, for jscpd, that the captured output respects the settled scope — G1).

## Notes

- jscpd/eslint/knip/depcruiser remain deliberately JS-scoped (see memory) — G1 is about the
  *invocation's* file coverage, not re-scoping the product.
- `js_base` itself (the probe) is KEPT; only the per-adapter output parsing is deleted.
