---
id: s1-t3-cli-bundle-and-delete-sarif-layer
kind: task
project: code-review
status: done
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, s0-contract-inversion-and-bundle.md]
created: 2026-05-30
updated: 2026-05-31
tags: [cli, bundle, deletion, teardown, capstone]
---

# Task s1-t3 — CLI emits the bundle + delete the SARIF normalisation layer

## Outcome

`polyreview run` collects per-tool `CaptureOutput`s and emits a `review-bundle.v1.json`-valid
`ReviewBundle`; the entire normalisation layer is deleted. This is the capstone that
completes the strangle — after it, no SARIF-aggregation code exists.

## Design

**CLI rewrite (`cli.py`):**
- `_run_analyzers` runs the migrated adapters (each returns a `CaptureOutput`) and builds a
  `ReviewBundle(request, outputs=tuple(captures))` → `bundle_to_json`. Delete `aggregate`,
  `_merge_metrics`, `compute_hotspots`, `_output_to_dict`, `_safe_run`'s `AnalyzerOutput`
  return (replace with a `CaptureOutput`-returning safe wrapper).
- Replace the `review-response.json` validation with `load_bundle_schema()` /
  `review-bundle.v1.json` validation.
- Exit-code logic: `has_error = any(c.status in {"error", "timeout"} for c in captures)` →
  non-zero (preserve the current "any analyzer error → exit 1" behaviour; decide whether
  `timeout` counts as error for exit purposes and document it).
- The `--output` summary line (`analyzers/findings/duration`) loses `findings` (no parsed
  findings now) — report `analyzers` + per-tool `status` counts + total `duration_s` from
  the captures instead.

**Deletions (the fragile half):**
- `code_review/aggregator.py`, `code_review/severity.py`, `code_review/hotspots.py`.
- The SARIF builders in `code_review/adapters/sarif_utils.py` (delete the module if nothing
  else uses it).
- `MetricSet` and the `sarif`/`metrics` fields of legacy `AnalyzerOutput` in `contracts.py`
  (delete legacy `AnalyzerOutput` entirely if s1-t0 kept `CaptureOutput` as the name).
- `code_review/schemas/review-response.json` (the old CLI output contract) — or retain only
  if some non-CLI consumer needs it (confirm by grep; likely delete).
- All dedicated SARIF-correctness / aggregator / hotspots / severity test suites.
- `config.py` fields that only fed the deleted layer (`dedup_line_tolerance`,
  `hotspot_weights`, `severity_overrides`) — remove and update `code-review.toml.example`
  + config tests. Keep `disabled_analyzers`, `contract_testing`, `semgrep_rules`.

**Absorb s0 story-level Minors #2/#3:**
- Add a `timeout`-status capture to the bundle test suite (Minor #2).
- Clean the `test_capture` timeout-test event-loop-teardown warning — await/close the killed
  subprocess transport (in `base.run_subprocess`, now fair game to touch) or filter the
  known warning (Minor #3).

## Acceptance criteria

- `polyreview run` on a fixture emits JSON that **validates against `review-bundle.v1.json`**
  (golden-bundle test); the bundle carries one `outputs` entry per selected analyzer with
  raw stdout/stderr.
- Process exit code is non-zero iff a capture has `status=="error"` (timeout disposition
  documented); zero on an all-`ok`/`unavailable` run.
- `grep -r` finds **zero** references to `aggregate`, `severity`, `hotspots`, `MetricSet`,
  `_to_sarif`, `compute_hotspots`, `review-response.json` in `code_review/` (outside this
  task's own deletion diff).
- `config.py` no longer exposes the removed fields; `code-review.toml.example` + config
  tests updated; remaining config options still load.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean. Net LOC drops
  materially (target: the ~357 LOC of aggregator/severity/hotspots + the `_to_sarif` bodies).
- The s0 timeout-teardown warning no longer appears in the suite run; a `timeout` capture is
  serialised and schema-validated in the bundle tests.

## Test specification (write first, confirm RED)

1. `tests/test_cli_bundle.py` (new) — `test_run_emits_valid_bundle`: invoke the CLI
   (CliRunner, `capture="fd"`) on a small fixture with a couple of analyzers; parse stdout;
   `jsonschema.validate` against `review-bundle.v1.json`; assert one `outputs` entry per
   analyzer with non-empty `command`.
2. `test_run_exit_code_on_error` — a fixture/stub where one capture is `error` → CLI exits
   non-zero; an all-`ok` run exits zero.
3. `test_bundle_includes_timeout_capture` (in `tests/test_review_bundle.py`) — a `timeout`
   capture serialises and validates (Minor #2).
4. `test_capture_timeout_no_loop_teardown_warning` (or a `filterwarnings` assertion) — the
   timeout path no longer emits `RuntimeError: Event loop is closed` (Minor #3).
5. Delete (don't adapt) `tests/test_aggregator*.py`, `tests/test_hotspots*.py`,
   `tests/test_severity*.py`, and the per-adapter SARIF-schema tests; the suite must stay
   green after deletion.

## Notes

- Do this task only after s1-t0/t1/t2 — every adapter must already return `CaptureOutput`,
  or the CLI rewrite has nothing coherent to collect.
- **Diff-path resolution** (open item): the CLI rewrite touches `_run_analyzers`'
  `resolve_diff_paths(Path.cwd(), diff)` — if the repo-relative-vs-cwd-abspath mismatch is
  cheap to fix in passing, do it and note it; otherwise carry to s2.
- This is a large, deletion-heavy diff — expect the **story-level Review** right after close
  to scrutinise the teardown for orphaned imports/dead config.

## Close (2026-05-31)

The strangle is complete: `polyreview run` now collects one raw `CaptureOutput` per analyzer
into a `ReviewBundle` and emits `review-bundle.v1.json` directly — **no SARIF aggregation
remains**. Tests-first (RED: `test_cli_bundle.py` failed against the old `analyzers`/`sarif`
shape), then GREEN. **Net −1604 LOC** (37 files, +351/−1955).

**Deleted:** `aggregator.py`, `severity.py`, `hotspots.py`, `adapters/sarif_utils.py`,
`schemas/review-response.json`; `MetricSet` + legacy `AnalyzerOutput` from `contracts.py`;
the `cli.py` shims (`_capture_to_legacy`/`_output_to_dict`/`_merge_metrics`); the
`capabilities.json` `hotspots` block; 5 SARIF-layer test suites (aggregator/hotspots/
severity/sarif_utils/cli_aggregation). `config.py` stripped to `disabled_analyzers` +
`semgrep_rules` (dropped dedup/severity/hotspot knobs); `code-review.toml.example` + SKILL.md
output description updated.

**CLI:** `_safe_run` returns a `CaptureOutput` (adapter crash → `error` capture, `tool`=name,
no traceback leak). **Exit code:** non-zero iff any capture is `error` **or** `timeout` (a
timed-out tool analysed nothing — documented at `cli.py`); `unavailable`/`ok` → 0. `--output`
summary replaced findings-count with per-status counts + total duration. Schema validation is
non-fatal-by-warning, against the actually-emitted JSON.

**s0 Minors absorbed:** #2 — a `timeout` capture is serialised + schema-validated
(`test_review_bundle.py`). #3 — `base.run_subprocess` reaps the killed child on timeout,
**bounded** by `asyncio.wait_for(proc.wait(), 5.0)` (an earlier unbounded `await proc.wait()`
hung the run when a real multi-process analyzer — node/semgrep — was killed; the 5s cap fixes
that while still silencing the GC "Event loop is closed" warning).

**Gate:** `uv run pytest` **361 passed** (`-m "not integration"`) + **15 integration passed**;
`ruff` + `mypy code_review` clean. AC deletion-grep clean on source. Real-run path proven
manually: `polyreview run --analyzer bandit --target <file>` emits a valid bundle with
bandit's raw JSON verbatim on `stdout`.

**Verify:** PASS (all 6 ACs evidenced, no drift). **Review:** MINOR-ONLY (0 Critical/
Important). Remediated inline: build the bundle dict once + validate the emitted bytes (perf
nit); reworded a stale `review_bundle.py` doc comment; added two coverage tests
(`timeout`→non-zero exit; `--output` per-status counts). The `test_cli_defaults_to_quick...`
target was scoped from `.` to an isolated tmp dir — both Verify and Review confirmed this is
a legitimate fix (its `--target .` scanned the vendored `node_modules`/`.venv` with the real
toolchain, taking minutes; the assertion is only about CLI defaulting), not a weakened test.

**Carried to s2:** `schemas/sarif-2.1.0.json` is now dead data — no source loads it after
`sarif_utils.py` was deleted (eslint/trivy still emit SARIF to stdout, captured raw, but
nothing validates against the schema). Kept (out of this task's deletion list; packaging
tests assert it) — operator decision to retain-with-rationale or remove. Diff-path resolution
(`resolve_diff_paths(Path.cwd(), diff)`) unchanged — still carried to s2.
