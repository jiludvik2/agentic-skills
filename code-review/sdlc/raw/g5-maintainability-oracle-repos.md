# Raw capture — G5 maintainability-scanner test oracle: candidate fixture repos

**Captured:** 2026-05-30
**Origin:** addresses **G5** from `sdlc/raw/post-coverage-eval-findings.md` — "maintainability
scanners (vulture/radon/cohesion/pydeps + JS depcruiser) have no documented oracle; their
precision can't be judged on a vuln app." This note shortlists public repos with *labelled*
dependency/coupling structure to serve as known-answer fixtures, focused on **pydeps** (Python
coupling/cycles) and **depcruiser** (JS/TS coupling/cycles).

## The thought

Build the G5 oracle from **tool-owned fixtures** rather than real-world apps: the tools' own test
suites already encode the expected graph/cycles as assertions, so the expected-findings set is
known and MIT-licensed. Vendor a small labelled fixture set into the analyzer-coverage QA harness
(`sdlc/docs/qa/analyzer-coverage/`) and assert pydeps/depcruiser findings against it in CI.

## Tier 1 — tool-owned fixtures (labelled, known-answer) — preferred

### pydeps — `thebjorn/pydeps` (`tests/`)
- `test_cycles.py` — cycle-detection oracle; assertions encode expected cycles.
- Docs' canonical fixture: a `cycles/` package — `a.py` (`from . import b`), `b.py`
  (`from . import a`); run `pydeps cycles --show-cycles`. Minimal known-cycle input.
- `test_relative_imports.py` + the `relimp` fixture — relative-import resolution.
- `filemaker.py` — helper that **generates fixture package trees dynamically**; reusable to
  synthesize labelled graphs of arbitrary shape. `simpledeps.py` is a sample module.

### depcruiser — `sverweij/dependency-cruiser` (`test/`)
- `test/extract/__mocks__/` — VERIFIED: ~30 mock source trees by module system + shape
  (`cjs`, `es6`, `ts`, `ts-types`, `vue`, `amd`, `coffee`; graph shapes `reachable`, `maxDepth`,
  `cache-busting-*`). Ready-made known-graph inputs.
- Circular-dependency assertions live at the **enrich/derive** stage, not extract — look under
  `test/enrich/` (`derive/circular/`) and `test/validate/` (`no-circular` rule fixtures).
  NOT yet verified to an exact folder; resolve on clone with the grep below.

## Tier 2 — sibling tools whose fixtures are reusable as input data
- `bndr/pycycle` (Python) — `tests/` ship deliberately circular sample projects; reusable as
  pydeps input.
- `pahen/madge` (JS/TS) — `test/` circular fixtures (`moduleA → moduleB → moduleA`); cross-check
  input for depcruiser.

## Tier 3 — curated real-world demos (realistic, lightly labelled)
- React+TS via madge (dev.to/greenroach) and Misskey via dependency-cruiser (algonote.com) — real
  apps with *documented* cycles; heavier, closer to a production oracle than synthetic fixtures.

## Resolve-on-clone commands
```bash
# depcruiser: locate cycle/orphan-specific mock trees
git clone --depth 1 https://github.com/sverweij/dependency-cruiser
grep -rl "circular\|orphan" dependency-cruiser/test --include=*.spec.*

# pydeps: minimal known-cycle package + the dynamic generator
git clone --depth 1 https://github.com/thebjorn/pydeps
sed -n '1,40p' pydeps/tests/test_cycles.py   # expected-cycle assertions
```

## Open questions for compile
- Scope: G5 is currently a *method gap* note; this could become a QA-harness story (extend
  `analyzer-coverage/` with a labelled coupling-fixture set + expected-findings JSON) rather than a
  product-code change. Pairs naturally with whichever epic round picks up G2 (vulture FP tuning),
  since both need a precision target.
- Coverage breadth: pydeps + depcruiser are graph/cycle tools with clean labelled oracles. radon
  (complexity), cohesion, and vulture (dead code) need *different* labelled fixtures (known hotspots
  / known-dead symbols) — out of scope for this repo shortlist; flag separately.
- Licensing/vendoring: confirm MIT terms before vendoring tool fixtures into the harness; or
  reference by pinned commit + fetch in setup rather than copy.

**Verification confidence:** pydeps `test_cycles.py`/`cycles` package and depcruiser
`test/extract/__mocks__` confirmed directly; depcruiser cycle-specific mock path inferred to the
enrich/validate stage (grep above resolves it).
