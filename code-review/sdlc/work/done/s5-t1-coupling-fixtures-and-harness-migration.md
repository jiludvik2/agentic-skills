---
id: s5-t1-coupling-fixtures-and-harness-migration
kind: task
project: code-review
status: done
parent: s5-maintainability-oracle
sources: [s5-maintainability-oracle.md, s5-t0-bundle-oracle-module.md, adr-0020-thin-invocation-runner.md, qa-analyzer-coverage.md]
created: 2026-05-31
updated: 2026-05-31
closed: 2026-05-31
notes: |
  Verifier PASS / reviewer MINOR-ONLY (no Critical/Important; no fix tasks). Two labelled
  coupling fixtures added (python/cyclepkg a↔b import cycle; js/__mocks__ prod→mock edge),
  regenerable via scaffold_fixtures.sh (verified idempotent, zero drift to the 13 existing
  fixtures). run_smoke.py fully migrated off the deleted consolidated schema to the review
  bundle via bundle_oracle (status_of + output_for(...).stdout → extractor); dead readers
  (_count_findings/_expect_radon/_expect_pydeps_metrics) removed; CASES now 14 with a
  label≠analyzer split (pydeps/pydeps-cycles and depcruiser/depcruiser-mocks share one
  --analyzer id, distinct .qa_<label>.json files — no collision). Added pydeps_max_fanout
  helper. In-sandbox pydeps integration test (real tool → pydeps_has_cycle True; RED before
  the fixture existed) + a fixture-contract guard. Gates: 26 QA tests + 391 full suite green,
  ruff + mypy clean. Carry-forward to s5-t2 (per spec, not a defect): confirm depcruiser
  scanning `src` actually resolves the ../__mocks__ cross-dir edge against the real binary;
  adjust the fixture root if not (fixture-only). Full real-toolchain run is s5-t2.
tags: [qa, fixtures, coupling, harness, bundle, test-first]
---

# Task s5-t1 — labelled coupling fixtures + run_smoke.py migration (the wiring)

## Outcome

The two labelled coupling fixtures exist and are regenerable, and `run_smoke.py` reads the
`review-bundle.v1.json` the CLI now emits, routing every case through `bundle_oracle`
(s5-t0) — including the two new precision coupling cases. The dead consolidated-schema
readers are gone. A real, in-sandbox pydeps integration test proves the pydeps precision
oracle end-to-end (pure-Python, no heavy provisioning); the depcruiser path is exercised by
the manually-run full harness (node-dependent) and validated in s5-t2.

## Files to add / change

1. **New fixture — pydeps `test_cycles`:** `fixtures/python/cyclepkg/` with a labelled
   `a → b → a` import cycle:
   - `__init__.py` (empty), `a.py` → `from cyclepkg import b`, `b.py` → `from cyclepkg import a`.
   - Keep it minimal and unambiguous so pydeps' dotted module keys are stable
     (`cyclepkg.a`, `cyclepkg.b`).
2. **New fixture — depcruiser `__mocks__`:** under `fixtures/js/` a labelled prod→mock
   coupling edge:
   - `src/app.js` → `import "../__mocks__/service.js"` (production source importing a mock).
   - `__mocks__/service.js` → a trivial module (e.g. `export const svc = 1;`).
   - This plants the **specific** non-mock-source → `__mocks__/` edge the s5-t0 oracle
     asserts. (Distinct from the existing `src/cycle_a/cycle_b` circular case.)
   - Match the existing `fixtures/js` module style (the repo's JS fixtures are ESM `.ts`/`.js`
     under `src/`); use whatever extension/import form depcruiser resolves with the adapter's
     vendored config — confirm against the real run in s5-t2.
3. **`scaffold_fixtures.sh`** — add generation blocks for both new fixtures so
   `fixtures/` stays fully regenerable (the file documents itself as the regenerator).
4. **`run_smoke.py` — migrate orchestration onto the bundle:**
   - Replace the consolidated readers: delete `_count_findings`, `_expect_radon`,
     `_expect_pydeps_metrics`, and the `consolidated["analyzers"][name]` status path in
     `_evaluate`.
   - `_evaluate` now: load the bundle JSON the CLI wrote, call
     `bundle_oracle.status_of(bundle, name)` for the adapter status, and call the
     case's oracle (a `bundle_oracle` extractor) on `output_for(bundle, name)["stdout"]`.
   - Update the `CASES` table: each existing case keeps its loose intent but points at the
     matching `bundle_oracle` extractor; **add two cases**:
     - `("pydeps-cycles", PY, "cyclepkg", <pydeps_has_cycle a,b>, "labelled a→b→a import cycle")`
       — or fold into the existing pydeps case if you prefer one pydeps row asserting the
       precise cycle (recommended: a dedicated row, so the loose fan-out case and the precise
       cycle case are both visible).
     - `("depcruiser-mocks", JS, ".", <depcruiser_has_edge_into "__mocks__">, "prod→__mocks__ coupling edge")`.
   - Keep the existing `depcruiser` (`cycle_a/cycle_b`) case, migrated to
     `depcruiser_has_circular`.
   - Import `bundle_oracle` as a sibling module (same dir) — `from bundle_oracle import ...`
     works because `run_smoke.py` runs as a script from that dir; if invoked from the repo
     root, add the dir to `sys.path` (it already resolves `HERE`).
5. **New test — in-sandbox pydeps integration:** `tests/test_qa_pydeps_cycle.py`
   (`@pytest.mark.integration` if the repo marks integration tests; pydeps needs **no** node
   /brew/network so it runs in-sandbox under `uv run`). It: runs `python -m pydeps
   fixtures/python/cyclepkg --show-deps --no-output --noshow` (or invokes the CLI with
   `--analyzer pydeps` and reads the bundle), feeds the raw stdout to
   `bundle_oracle.pydeps_has_cycle(..., "cyclepkg.a", "cyclepkg.b")`, and asserts `True`.
   This is the genuine red→green proof the precision oracle works against the real tool.

## Acceptance criteria

- `fixtures/python/cyclepkg/` and `fixtures/js/__mocks__/` exist with the labelled defects
  above and are regenerated cleanly by `scaffold_fixtures.sh` (run it, diff = no surprise).
- `run_smoke.py` contains **no** reference to `consolidated[...]`, `_count_findings`,
  `_expect_radon`, or `_expect_pydeps_metrics`; all evaluation goes through `bundle_oracle`.
- `CASES` includes the two new precision coupling rows; the report/console summary render
  them like any other row.
- The pydeps integration test passes in-sandbox: real pydeps on `cyclepkg` →
  `pydeps_has_cycle` `True`. It fails (RED) before `cyclepkg` exists / before the oracle is
  wired.
- No change to any adapter, `capabilities.json`, or the `code_review/` package.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean. (Running the
  *full* `run_smoke.py` end-to-end is **not** an AC of this task — it needs the heavy
  toolchain and is validated in s5-t2; this task is verified by the oracle unit tests
  (s5-t0), the pydeps integration test, and code review of the migration.)

## Test specification (write first, confirm RED)

1. **pydeps integration** (`tests/test_qa_pydeps_cycle.py`) — described above. RED before the
   fixture + oracle wiring exist; GREEN after. The single automated, real-tool proof of a
   precision oracle that fits in-sandbox.
2. **Fixture presence/shape** — a cheap test (can live in the same file) asserting the
   fixture files exist with the expected import lines, so a future `scaffold_fixtures.sh`
   edit that drops the planted edge fails loudly. (Optional but recommended; the planted
   defect is the contract.)
3. The s5-t0 oracle unit tests already cover the depcruiser edge-into logic against a
   snippet; depcruiser's *real* output is validated in s5-t2's provisioned run (node needed),
   so there is no in-sandbox depcruiser integration test here — call this out in `## Notes`
   rather than faking one.

## Notes

- depcruiser needs `node` + vendored `dependency-cruiser`; that is the heavy path, so its
  end-to-end proof lives in the manually-run harness (s5-t2), not in `tests/`. Do not write
  an in-sandbox depcruiser test that would silently skip — the unit-level oracle test
  (s5-t0) plus the s5-t2 provisioned run are the coverage.
- The exact depcruiser resolution (does the adapter's vendored config follow the
  `../__mocks__/service.js` import and emit the edge with a `resolved` path containing
  `__mocks__/`?) is confirmed in s5-t2 against the real binary. If the config does not
  resolve cross-dir imports, adjust the fixture layout (keep `app.js` and `__mocks__/`
  siblings under one root the config scans) — fixture-only change, no adapter change.
- ADR-0020: the harness reads raw output; do not reintroduce any normalization.
