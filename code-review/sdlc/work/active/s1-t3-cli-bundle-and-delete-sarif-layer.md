---
id: s1-t3-cli-bundle-and-delete-sarif-layer
kind: task
project: code-review
status: active
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, s0-contract-inversion-and-bundle.md]
created: 2026-05-30
updated: 2026-05-30
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
