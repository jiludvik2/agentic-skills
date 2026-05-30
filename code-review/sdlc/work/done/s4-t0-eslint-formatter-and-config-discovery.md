---
id: s4-t0-eslint-formatter-and-config-discovery
kind: task
project: code-review
status: done
parent: s4-eslint-adapter-robustness
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-30
updated: 2026-05-30
tags: [eslint, adapter, sarif-formatter, node, cwd]
---

# s4-t0 — eslint formatter resolution + config-discovery robustness

## Outcome

The eslint adapter resolves `@microsoft/eslint-formatter-sarif` itself from the
vendored `node_modules` (absolute formatter path, or `NODE_PATH` set by the adapter
on the subprocess env — not by the caller), and its integration test runs without
the smoke harness's `NODE_PATH`/cwd scaffolding. The formatter-resolution half is a
real adapter defect (F8); the config-discovery half is a robustness/test fix.
Single coherent adapter change implementing all three s4-story scenarios. Depends on
s1 (vendored toolchain).

## Acceptance criteria

(The s4-story scenarios are the contract; restated as the per-task gate.)

### Scenario: SARIF formatter resolves regardless of cwd
- **Given** the adapter run from any cwd with the vendored toolchain
- **When** it builds its command
- **Then** the SARIF formatter resolves (absolute path or adapter-set `NODE_PATH`)
  and eslint does not error on formatter loading.

### Scenario: integration test runs without harness scaffolding
- **Given** `tests/test_adapters/test_eslint.py::test_eslint_integration_*`
- **When** it runs with the toolchain present (no external `NODE_PATH`, no manual
  cwd change)
- **Then** it returns `status=ok` and valid SARIF with the expected finding.

### Scenario: smoke harness drops the eslint NODE_PATH stopgap
- **Given** the analyzer-coverage harness after this task
- **Then** `run_smoke.py` no longer sets `NODE_PATH` (or special-cases eslint's cwd)
  for the eslint case to pass.

## Test specification

Write first, confirm red, then implement. Extend
`tests/test_adapters/test_eslint.py`:

1. `test_eslint_formatter_resolves_from_arbitrary_cwd`: run the adapter from a cwd
   that is **not** the fixture dir, with a fixture flat config supplied to the
   target; assert `status=ok` and SARIF parses (no "problem loading formatter" /
   "couldn't find eslint.config" error).
2. Fix `test_eslint_integration_detects_console_log` to run without external
   `NODE_PATH` and to point eslint at a fixture with a discoverable flat config;
   assert it detects the planted rule violation.

## Notes

- Coordinates with **s1-t2**, which guarantees formatter *resolution* as a
  precondition; this task owns the adapter-side production mechanism and the
  self-sufficient integration test (F8). If s1-t2 already moved formatter
  resolution into the adapter, this task narrows to config-discovery robustness +
  dropping the harness stopgap — reconcile at execution.
- After this task the harness `NODE_PATH` stopgap is removed; confirm the smoke
  eslint case stays green without it.

## Closure (2026-05-30)

**Reconciliation outcome (as the task anticipated):** s1-t2 had already moved
formatter resolution into the adapter (absolute `NODE_PATH`) **and** the smoke
harness had already dropped its `NODE_PATH`/eslint-cwd stopgap. So scenarios 1 and
3 were pre-satisfied; this task narrowed to scenario 2 — the real integration test
— plus the config-discovery robustness that makes it self-sufficient.

**Implementation:** the adapter (`code_review/adapters/eslint.py`) now anchors the
eslint subprocess cwd at the targets' common-ancestor directory and passes targets
relative to it. eslint v9 discovers flat config by searching UPWARD from cwd and
treats cwd as the base path (targets outside it are silently ignored), so anchoring
makes the reviewed project's own `eslint.config.*` discoverable and keeps targets
within the base path — regardless of caller cwd. Uses `run_subprocess(cwd=…)`
(child-only), **not** `os.chdir`, so the CWD-anchored `cache_root()` contract (the
s6/s7 / ADR-0018 seam) is preserved; the absolute `NODE_PATH` decouples toolchain
location from the target cwd.

**Tests:** new fixture `tests/fixtures/js-eslint/` (own flat config + planted
`no-console`/`no-unused-vars`); `test_eslint_integration_detects_console_log` de-
xfailed, points at the fixture, asserts status=ok + ≥1 finding + a planted rule
fired (no chdir, no external `NODE_PATH` — same `target_paths=(str(FIXTURE),)`
idiom as depcruiser/jscpd). Meta-gate `test_node_integration_gating.py` flipped
eslint `must_xfail` True→False (last remaining xfail; suite now 0 xfailed).

**Verify:** PASS (fresh-context verifier) — all three scenarios met, TDD honoured,
logic non-regressive, gates green.

**Review dispositions (story-level reviewer, HAS-CRITICAL-OR-IMPORTANT):**
- *Critical* (single non-existent target → cwd = file path → subprocess crash):
  ACCEPTED. Empirically confirmed (existing single file worked; a missing single
  file crashed with `[Errno 2]` on cwd). Fixed the invariant `isfile`→`not isdir`
  so the anchor is always an existing directory; added RED-first unit test
  `test_eslint_anchors_cwd_at_existing_directory_for_missing_file` + integration
  `test_eslint_integration_single_file_target`.
- *Important* (disjoint targets collapse anchor to a far ancestor): PARTIALLY
  ACCEPTED. eslint v9's model is a single flat config at the project root governing
  the tree, so common-ancestor anchoring is correct; per-package grouping would be
  over-engineering. Documented the single-project assumption in the adapter comment
  instead of adding grouping logic.
- *Minor* (no shared helper across JS adapters): DECLINED (YAGNI — one caller; the
  comment explains eslint's uniqueness).
- *Minor* (diff paths `abspath`'d against `Path.cwd()` can mis-resolve from a
  subdir): PRE-EXISTING, cross-cutting (`resolve_diff_paths` returns repo-relative
  paths), not regressed by this diff. Logged as a STATE follow-up; the `isdir` fix
  removes the hard crash.
- *Minor* (stale "skill root" NODE_PATH comment) + *Nit* (gating docstring lumping
  knip with the F-tracked set): FIXED.

**Gates:** `uv run pytest -m 'integration or not integration'` → **384 passed**
(0 xfailed); `ruff check .` clean; `mypy code_review` clean.
