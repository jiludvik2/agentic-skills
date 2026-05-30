# Post-GA self-review findings (2026-05-30)

Source: dogfooding run — `polyreview run --depth full --scope story-level --target code_review`
(all 13 analyzers). Verdict: clean — 62 findings, **all `sdlc_severity: nit`**, zero
Critical/Important/Minor. Two items worth compiling into post-GA work; the rest
(cohesion 23, jscpd 13, vulture 21, pydeps 4) are known false-positive shapes
(dataclasses/enums/protocols/single-method adapters; deliberately-parallel adapter
structure; FP-prone dead-code) — capture as "noise, do not action" unless a
whitelist/threshold tuning task is opened.

## Finding 1 — bandit B110: swallowed exception in schemathesis adapter

`code_review/adapters/schemathesis_.py:141` — inside `_run_operation._sync`:

```python
try:
    case.call_and_validate(additional_checks=[response_schema_conformance], session=session)
except FailureGroup as fg:
    failures.extend(fg.exceptions)
except Exception:
    pass            # ← B110
return failures
```

**Problem:** a non-`FailureGroup` exception during the actual API call+validate
(connection error, a bug in validation, an unexpected schemathesis error) is
swallowed and the operation is reported with **zero** conformance failures — a false
"API conforms" for a contract-testing tool. Distinct from the line-130 `except
Exception: return []` after `h_find`, which is a deliberate skip of unsatisfiable
strategy generation (and already re-raises `Unsatisfiable`/`Flaky`).

**Recommended fix (design decision):** do **not** re-raise (one bad operation
shouldn't fail the whole adapter run). Instead **surface** the swallowed error as a
synthetic SARIF finding for that operation — e.g. `ruleId
"schemathesis.execution-error"`, level `error`, message naming the operation + the
exception — so "couldn't test it" is visible, not hidden behind a clean result.
Reuse `_failure_to_sarif_result`'s location/shape conventions.

**Test spec (tests-first):** in `tests/test_adapters/test_schemathesis.py`, patch
`call_and_validate` to raise a plain `RuntimeError`; assert `_run_operation` (or the
adapter) yields one `schemathesis.execution-error` finding naming the operation,
rather than an empty list. Mirror the existing mock style (MagicMock op +
`fake_run_operation`/patch on schemathesis internals).

Severity: nit (low-confidence bandit check, least-used analyzer) — but a real
correctness smell for a conformance tool. One-commit task.

## Finding 2 — JS analyzers error on a pure-Python target (UX rough edge)

`--review maintainability --depth full --target code_review` (Python-only) invoked
the JS-only analyzers and they **errored** instead of skipping:

- `eslint` → `eslint exited 2: ... ESLint: 9.` (flat-config / no JS to lint)
- `knip`   → `knip exited 2: Unable to find package.json`

`jscpd` (language-agnostic) ran fine. The `maintainability` domain bundles JS-only
subcategories (`duplication`/`quality`), whose adapters surface `status: error`
when the target tree has no JS / no `package.json`, polluting an otherwise-clean
Python review with two red analyzers.

**Recommended direction (needs an ADR-level call):** a JS adapter pointed at a
target with no JS files / no `package.json` should report `status: "unavailable"`
(or a new `skipped`) with a reason — same graceful-skip contract as a missing
binary — rather than `error`. Decide **where** the no-JS detection lives: the
adapter's runtime availability probe (`_probe_analyzer`/`probe_js_adapter`), the
selector (don't select JS analyzers when the diff/target has no JS — but `--target`
has no language signal today), or per-run inside the adapter. Cheapest correct
spot is likely the adapter run: detect "no `package.json` under target / no JS
files" → return `unavailable`, not `error`.

Touches `eslint.py`, `knip.py`, possibly `js_base.py`. Bigger than finding 1 —
warrants an ADR (the error-vs-unavailable contract is cross-adapter) + a task.

## Suggested compilation

- A small post-GA story (e.g. `post-ga-analyzer-polish`) with two tasks:
  - t0: schemathesis swallowed-exception → surface as `execution-error` finding (Finding 1).
  - t1: JS analyzers report `unavailable` not `error` on no-JS targets (Finding 2) — preceded by an ADR on the error-vs-unavailable contract.
- Or two standalone tasks. Finding 1 is self-contained; Finding 2 needs the ADR first.
