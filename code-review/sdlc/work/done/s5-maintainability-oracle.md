---
id: s5-maintainability-oracle
kind: story
project: code-review
status: done
parent: epic-analyzer-thin-runner
children:
  - s5-t0-bundle-oracle-module
  - s5-t1-coupling-fixtures-and-harness-migration
  - s5-t2-regenerate-captures-and-docs
sources: [epic-analyzer-thin-runner.md, adr-0020-thin-invocation-runner.md, qa-analyzer-coverage.md]
created: 2026-05-31
updated: 2026-05-31
closed: 2026-05-31
close-notes: |
  All three tasks done; each verifier PASS / reviewer MINOR-ONLY. Story-level review
  MINOR-ONLY (ADR-0020 contract upheld — no normalization creep; fixtures regenerate with
  zero drift; both precision oracles sound and proven against real binaries). G5
  architecture-validation CONFIRMED: adding the two precision coupling oracles needed zero
  adapter change — the third of three thin-runner "near-trivial" proofs (s3 ruleset, s4
  analyzer, s5 oracle).

  Delivered: pure `bundle_oracle.py` (per-tool raw-native signal extractors + pydeps
  import-cycle and depcruiser prod→__mocks__ precision oracles), two labelled coupling
  fixtures (cyclepkg, js/__mocks__), in-sandbox pydeps integration test, and the full
  bundle-migration of run_smoke.py off the deleted consolidated schema. The first real
  end-to-end run after the migration caught a cluster of real regressions (FINDINGS F11–F15:
  CLI run-subcommand staleness, trivy SARIF-vs-native, stale schemathesis invocation,
  couplingpkg leading-zero crash) — exactly the anti-silent-degradation property G5 adds.
  Final harness: 13/14 pass, 1 xfail (gitleaks — real shipping-adapter defect emitting no
  JSON on stdout, filed as fu-gitleaks-json-output-capture + recommended adapter
  output-capture audit, out of s5 scope). All 14 results/raw/*.json schema-valid; 391-test
  suite + ruff + mypy clean. Commits e2687c9 (t0), d3cffe4 (t1), 9ee69ce (t2), c81bbde
  (t2 close).

  Parked Minors (story-level review, opportunistic): bundle_oracle.py count_trivy +
  count_schemathesis are now dead (trivy→count_sarif_results; schemathesis removed) — clean
  up on next QA touch; FINDINGS.md H1 date; README "native JSON" one-liner overstates
  gitleaks; _run_cli temp-file unlink-on-failure. None blocking.
tags: [qa, maintainability, coupling, oracle, bundle, architecture-validation]
---

# Story s5 — G5: maintainability oracle (coupling precision oracles on the raw bundle)

## Why

This is the epic's **third and final architecture-validation** (G5). ADR-0020 claims that
adding a *precision oracle* on the new thin-runner design must be **near-trivial** — the
oracle reads each tool's raw native output straight from the bundle, no normalization layer
to extend. s3 (JS semgrep rules, zero adapter change) and s4 (jscomplexity, one additive
adapter) proved the "add coverage" half; G5 proves the "add a *check on precision*" half.
If asserting that a coupling tool detects a specifically-planted cycle is hard, the
architecture is wrong.

There is also a **forcing function**: the analyzer-coverage QA harness
(`sdlc/docs/qa/analyzer-coverage/run_smoke.py`) is **currently broken**. Every one of its
oracles reads the pre-ADR-0020 consolidated schema (`consolidated["sarif"]`,
`consolidated["metrics"]`, `consolidated["analyzers"][name]["status"]`), but s1-t3 deleted
that aggregation layer and switched the CLI to emit `review-bundle.v1.json` (raw per-tool
output). So the harness cannot read the CLI's output at all, and the captured
`results/raw/*.json` are stale pre-bundle snapshots. s5 re-points the whole oracle at the
bundle contract — and the two new coupling fixtures are the headline G5 deliverable that
proves the re-pointed oracle has *precision*, not just *coverage*.

## What "maintainability oracle" means here (G5)

An **oracle** is the assertion that decides whether a planted defect was actually detected.
Today most oracles are loose (`_expect_findings(1)` — "tool emitted ≥1 result"). A loose
oracle still passes when a tool silently degrades (runs clean, finds nothing). G5 adds
**precision oracles** for the two *coupling* analyzers: each new fixture plants a *labelled,
known* coupling defect, and the oracle asserts that *that specific* defect appears in the
tool's raw output — not merely that some signal exists.

- **pydeps `test_cycles`** (Python) — a package with a labelled import cycle `a → b → a`.
  Oracle: parse pydeps' raw dependency-graph JSON and assert the **mutual back-edge** exists
  (`a.imports` contains `b` **and** `b.imports` contains `a`). Verified viable during
  planning against real pydeps with **zero adapter change** (`pydeps --show-deps` already
  emits per-module `imports`/`imported_by`).
- **depcruiser `__mocks__`** (JS) — a labelled coupling smell where production code depends
  on a `__mocks__/` module (prod→test-scaffolding coupling). Oracle: parse depcruiser's raw
  module graph and assert the **specific edge** from the non-mock source into `__mocks__/`
  exists. This is a *distinct* signal from the existing `cycle_a/cycle_b` circular case, so
  it adds real coverage rather than duplicating it.

  > **One interpretive call for operator confirmation.** The surviving epic/STATE text only
  > says "depcruiser `__mocks__`"; the raw G5 source (`g5-maintainability-oracle-repos.md`)
  > was absorbed at compile and is gone. Two readings fit: **(a, planned)** prod→`__mocks__`
  > coupling smell — distinct from the existing circular case, higher-value; **(b)** a second
  > circular fixture that just lives under a `__mocks__/` dir — symmetric with pydeps but
  > redundant with `cycle_a/cycle_b`. The plan below builds (a). Flip one AC in s5-t1 if you
  > meant (b).

## Scope

1. **Bundle oracle module** (`bundle_oracle.py`, co-located in the QA dir) — a pure,
   importable module that reads a `review-bundle.v1.json` dict, locates a tool's output, and
   extracts each tool's signal from its **raw native** stdout (the bundle carries native
   output, not SARIF-normalized — semgrep/eslint emit SARIF, but bandit/trivy/gitleaks/
   radon/knip/jscpd/pydeps/depcruiser emit their own JSON, vulture/cohesion text). Includes
   the two precision coupling oracles. Unit-tested in `tests/` against hand-authored bundle
   snippets — no binaries (s5-t0).
2. **Two labelled coupling fixtures** + `scaffold_fixtures.sh` regeneration, and the
   **migration of `run_smoke.py`** to read the bundle and route every case through
   `bundle_oracle` (deleting the dead consolidated-schema readers) (s5-t1).
3. **Regenerate `results/raw/*.json`** + the dated results report against the new bundle via
   a fully-provisioned harness run, and **reconcile the README** (raw-bundle shape, oracle
   module, the two new analyzer→fixture rows) (s5-t2).

## Decisions baked in (from planning)

- **Test strategy: pure oracle module + pytest** (operator-approved). Signal extraction is
  pure data transformation → unit-tested in `tests/` with captured snippets, red→green, no
  toolchain. `run_smoke.py` keeps only orchestration (subprocess + FastAPI lifecycle). The
  pydeps precision oracle additionally gets a **real in-sandbox integration test** (pydeps is
  pure-Python — no heavy provisioning); depcruiser's stays in the manually-run harness
  (node-dependent).
- **Oracle precision: assert the specific defect** (operator-approved) — for the two new
  coupling oracles. The other ~12 cases keep their existing loose semantics, merely
  re-pointed at native output (migrating them to precision is out of scope — that would be a
  separate hardening pass).
- **No new tool, no new pin, no adapter change.** s5 reuses the existing `pydeps` and
  `depcruiser` adapters as-is and only reads their raw output. No ADR needed (the bundle
  contract is already governed by ADR-0020).

## Out of scope

- Tightening the other ~12 oracles from loose (`≥1 finding`) to precision — separate pass.
- Any change to an adapter, `capabilities.json`, the selection scheme, or the shipping
  `code_review/` package beyond the new `tests/` files. The oracle module lives in the QA
  dir, not the package.
- TS coupling/complexity (carried as documented limitations from s3/s4).

## Acceptance criteria

- `bundle_oracle.py` exists in the QA dir as a pure module: a bundle reader + per-tool
  native signal extractors covering all 13 harness analyzers, including the two precision
  coupling oracles. No subprocess calls, no third-party binaries — importable and unit-tested.
- New fixtures: `fixtures/python/cyclepkg/` (labelled `a→b→a` import cycle) and
  `fixtures/js/__mocks__/` (labelled prod→`__mocks__` coupling edge), both regenerable via
  `scaffold_fixtures.sh`.
- `run_smoke.py` reads the `review-bundle.v1.json` the CLI now emits, routes every case
  (existing 12 + 2 new coupling cases) through `bundle_oracle`, and the dead consolidated
  readers (`_count_findings`, `_expect_radon`, `_expect_pydeps_metrics`, the
  `consolidated["analyzers"]` status path) are removed.
- pydeps precision oracle asserts the **specific** `a→b→a` back-edge; depcruiser precision
  oracle asserts the **specific** prod→`__mocks__` edge — each fails if the tool runs but
  the planted defect is absent (anti-silent-degradation).
- `results/raw/*.json` regenerated to the bundle shape; dated results report regenerated;
  README analyzer→fixture map + layout/contract sections reconciled to the bundle and the two
  new rows. A full provisioned harness run exits 0 (all analyzers produce their expected
  signal). *(This AC's harness run needs the heavy toolchain — see s5-t2; it may be
  operator-run outside the sandbox.)*
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean. (The QA module is
  outside `code_review/`, so mypy's package scope doesn't cover it; ruff `.` does.)

## Task sequence

- **s5-t0** — `bundle_oracle.py` pure module + `tests/` unit tests (incl. both precision
  coupling oracles) against hand-authored bundle snippets. Tests-first, verifiable
  in-sandbox. The brain of the harness.
- **s5-t1** — the two labelled coupling fixtures + `scaffold_fixtures.sh`; migrate
  `run_smoke.py` orchestration onto the bundle + `bundle_oracle`; add the in-sandbox pydeps
  integration test. The wiring.
- **s5-t2** — provisioned full-harness run: regenerate `results/raw/*.json` + results
  report; reconcile README/FINDINGS. The carry-over resolution + end-to-end validation
  (heavy toolchain; may be operator-driven outside the sandbox).

## Epic boundary (after s5 closes)

s5 is the **last story of `epic-analyzer-thin-runner`**. Closing it cleanly triggers the
epic-close work (not s5 tasks, handled at the boundary): **Document** — reconcile
`README.md` with the whole thin-runner epic; **File** — move the epic to `sdlc/work/done/`
and relocate the co-located ADRs (0020, 0021, 0022) from `sdlc/work/active/` to
`sdlc/docs/decisions/`, and the QA runbook stays in `sdlc/docs/`. Publication check
(rule #18): everything pushed to `origin/main`.

## Source

Compiled 2026-05-31 from `epic-analyzer-thin-runner.md` (s5 candidate-story description, G5;
"near-trivial precision oracle" validation criterion), `adr-0020-thin-invocation-runner.md`
(bundle contract), the `qa-analyzer-coverage` runbook + `run_smoke.py` read during planning,
the `review-bundle.v1.json` schema, and a live pydeps probe confirming cycle visibility in
raw output. Test-strategy and oracle-precision decisions: operator-approved 2026-05-31.
