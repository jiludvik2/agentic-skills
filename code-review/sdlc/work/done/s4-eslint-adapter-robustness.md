---
id: s4-eslint-adapter-robustness
kind: story
project: code-review
status: done
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-30
tags: [eslint, adapter, sarif-formatter, node, ga-readiness]
---

# s4 — eslint adapter robustness

## Summary

The eslint adapter only "passed" in the smoke harness because the harness set
`NODE_PATH` (so `@microsoft/eslint-formatter-sarif` resolves) and ran eslint with
cwd inside the fixture (where `eslint.config.js` lives). Run as the adapter
itself invokes it — `node <eslint> --format @microsoft/eslint-formatter-sarif
<targets>` from an arbitrary cwd — it returns `status=error` (FINDINGS.md F8):

- `ESLint couldn't find an eslint.config.(js|mjs|cjs) file` — flat-config lookup
  is relative to the process cwd, which the adapter doesn't control.
- The SARIF formatter resolves only because the harness sets `NODE_PATH`; the
  adapter passes a bare formatter name with no guarantee it resolves from the
  run cwd.

This surfaced as `tests/test_adapters/test_eslint.py::
test_eslint_integration_detects_console_log` failing once the Node toolchain is
installed (it skips in CI today — see F9 / s1). In the normal "review a JS
project from its root" path eslint finds that project's config, so the
config-discovery half is a robustness/test issue rather than a hard break; the
**formatter-resolution half is a real adapter defect**. Depends on s1 (vendored
toolchain).

## Acceptance criteria

### Scenario: SARIF formatter resolves regardless of cwd
- **Given** the eslint adapter run from any cwd (e.g. the repo root) with the
  vendored toolchain
- **When** it builds its command
- **Then** the `@microsoft/eslint-formatter-sarif` formatter resolves — via an
  absolute path derived from the vendored `node_modules`, or `NODE_PATH` set on
  the subprocess env by the adapter (not by the caller) — and eslint does not
  error on formatter loading.

### Scenario: integration test runs without harness scaffolding
- **Given** `tests/test_adapters/test_eslint.py::test_eslint_integration_*`
- **When** it runs with the toolchain present (no external `NODE_PATH`, no
  manual cwd change)
- **Then** it returns `status=ok` and a valid SARIF document with the expected
  finding — i.e. the test provides/locates a flat config deterministically and
  the adapter handles formatter resolution itself.

### Scenario: smoke harness drops the eslint NODE_PATH stopgap
- **Given** the analyzer-coverage harness after this story
- **Then** `run_smoke.py` no longer needs to set `NODE_PATH` (or special-case
  eslint's cwd) for the eslint case to pass — the adapter is self-sufficient.

## Plan

Single task — **s4-t0-eslint-formatter-and-config-discovery** carries the outcome
and the authoritative test specification. Depends on s1 (vendored toolchain).

## Closure (2026-05-30)

CLOSED via **s4-t0** (see its closure notes for detail). All three scenarios met:
scenarios 1 (formatter resolution) and 3 (smoke harness drops the NODE_PATH/cwd
stopgap) were pre-satisfied by s1-t2; scenario 2 (self-sufficient integration test)
landed here, enabled by adapter cwd-anchoring at the targets' root (child-only via
`run_subprocess(cwd=…)`, preserving the CWD-anchored `cache_root()` contract).
Story-level Review verdict HAS-CRITICAL-OR-IMPORTANT — Critical (cwd invariant) and
Important (single-project assumption) addressed in-task; remaining Minors
declined/deferred with rationale. F8 cleared. Suite 384 passed, 0 xfailed (last
Node-integration xfail flipped); ruff + mypy clean. Remaining epic blocker: F10
CLI errors (s5).
