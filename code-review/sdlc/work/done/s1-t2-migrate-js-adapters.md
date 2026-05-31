---
id: s1-t2-migrate-js-adapters
kind: task
project: code-review
status: done
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md, post-coverage-eval-findings.md]
created: 2026-05-30
updated: 2026-05-31
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

## Close (2026-05-31)

Tests-first (RED confirmed: 23 failing across the 4 rewritten test files before impl), then
GREEN. Full suite **415 passed** (`-m "not integration"`) + **15 integration passed** on the
vendored toolchain; `ruff check .` and `mypy code_review` clean.

**What landed:**
- All 4 JS adapters return `CaptureOutput`; `_to_sarif`/`normalise_sarif`/json-parse deleted
  from the JS set. Binary-absent flips **error → `unavailable`** (ADR-0019), matching
  semgrep/trivy. Invocation detail preserved + pinned by tests: eslint
  `NODE_PATH`+cwd-anchor+SARIF formatter (kept — eslint emits SARIF to stdout, captured
  verbatim, the parse is what's gone); depcruiser self-supplied `--config`+`--output-type
  json`+directory target; knip `--reporter json`+cwd; jscpd `--reporters json`+tempdir.
- `js_base.js_unavailable` (+ its `empty_sarif`/`AnalyzerOutput` imports) removed as orphaned
  by the migration. `probe_js_adapter`/`node_binary`/`has_js_files` kept.

**G1 disposition (AC line 52):** the settled jscpd scope is **`--format javascript,jsx,
typescript,tsx`** — exactly the JS/TS set, enforced at the invocation layer (`jscpd.py`).
By default jscpd auto-detects ~150 formats (HTML/CSS/markup/etc.); the pin confines detection
to JS/TS and nothing else, closing the real-app scope leak. Asserted three ways: the
invocation test pins the `--format` value, and the integration test asserts the real report's
`statistics.formats` ⊆ {javascript,jsx,typescript,tsx}. jscpd has no stdout-JSON reporter, so
the adapter runs it into a TemporaryDirectory and splices the report file onto
`CaptureOutput.stdout` verbatim.

**Verify:** PASS (all 6 ACs evidenced, no ADR-0020/0019 drift). **Review:** MINOR-ONLY
(0 Critical/Important). Remediated inline: jscpd **missing-report-on-OK now flips to `error`**
(was silently empty stdout — both verifier and reviewer flagged it as the regression that
would bite s1-t3's bundle emission), + a test for it; test fixture uses `Status.ERROR` not a
bare string. Nits (string literal vs `self.name` — matches semgrep/trivy idiom; duplicated G1
comment) dropped.

**Carried to s1-t3:** knip integration test asserts `unavailable` (the
`js-with-known-issues` fixture ships no top-level `package.json`, so the clean-skip fires
before knip runs) rather than a populated capture — honest given the fixture, but the only
one of the four integration tests not asserting a non-empty capture.
