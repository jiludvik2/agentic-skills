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

## Update — full-review test drive on deliberately-vulnerable repos (2026-05-30)

Ran `polyreview run --depth full --scope story-level` against two canonical OWASP
vuln apps: **PyGoat** (`adeyosemanputra/pygoat`, insecure Django, 80 py) → 462
findings (49 critical); **NodeGoat** (`OWASP/NodeGoat`, insecure Node, 50 js) → 184
findings (50 critical). This surfaced bugs the unit tests + clean-code self-review
never hit, because they only trigger on real-world repos. **These are Important
defects, not nits — they should lead the post-GA polish cycle, ahead of Findings 1–2.**

### Finding 3 (Important) — bandit adapter crashes: progress bar on stdout breaks JSON parse

`code_review/adapters/bandit.py:73` — `json.loads(result.stdout)` fails with
`invalid JSON: Expecting value: line 1` on PyGoat. **Root cause (confirmed by direct
repro):** newer bandit prints a Rich progress bar to **stdout** before the JSON:
```
Working... ━━━━━━━━━━━━━━━━━ 100% 0:00:00
{ "errors": [], ... }
```
The adapter assumes stdout is pure JSON. Intermittent — our small clean package
didn't trigger the bar; an 80-file repo did. **Impact: the primary Python SAST
scanner returns status=error / zero findings on a real Python codebase.**
**Fix:** add `-q`/`--quiet` to the bandit invocation (suppresses the bar), or strip
to the first `{` before `json.loads`. **Test (tests-first):** feed the adapter a
captured stdout that has the `Working... ━━━ 100%` prefix + JSON body; assert it
parses to findings, not status=error. One-commit fix.

### Finding 4 (Important) — eslint adapter crashes on real JS projects lacking flat config

`code_review/adapters/eslint.py` — eslint `exited 2` on NodeGoat. **Root cause
(confirmed):** NodeGoat has no `eslint.config.*` and no `.eslintrc`, and ESLint 9
*requires* a flat config, so it errors on any real-world JS project that hasn't
migrated to flat config. The adapter anchors cwd at the target root to discover the
project's config, but when there is none it surfaces a bare `eslint exited 2:` (empty
stderr). **Impact: the primary JS linter returns zero findings on a real JS app — the
common case, since most projects haven't migrated.** **Fix (design decision):** when
no flat config is found under the target, either (a) supply a built-in default flat
config so eslint can still run base rules, or (b) report `status: unavailable` with a
clear "no eslint flat config found" reason (graceful skip, same as Finding 2) rather
than a confusing `exited 2`. Needs a call on (a) vs (b). **Test:** run the adapter
against a JS tree with no eslint config; assert the chosen behaviour (findings from a
default config, or a clean `unavailable`), never a bare error.

### Finding 5 (coverage gap, not a crash) — semgrep SAST is thin

semgrep returned only **4** findings on PyGoat and **0** on NodeGoat. The vendored
ruleset (ADR-0016) is small and Python-first, so first-party code-vuln detection
badly underperforms the dependency/secret scanners. On both vuln apps, ~all 99
critical findings came from **trivy (dep CVEs)** + **gitleaks (secrets)**, not from
SAST. Consider broadening the semgrep ruleset (e.g. vendor `p/security-audit` /
language packs) or documenting the limitation. Likely an ADR-0016 revisit, not a quick fix.

### What works well (record, don't action)

trivy (133 / 76 real dep CVEs), gitleaks (10 / 3 real secrets incl. a private key),
jscpd, knip, cohesion, vulture all produced solid real-world signal.

## Suggested compilation

Priority order for a `post-ga-analyzer-polish` story (Findings 3–4 lead; they're the
ones that make polyreview miss first-party code vulns on real repos):

- t0 (Important): **Finding 3** — bandit `-q`/strip-to-`{`; tests-first with a
  progress-bar-prefixed stdout fixture. Self-contained, one commit.
- t1 (Important): **Finding 4** — eslint no-flat-config handling; needs the (a)
  default-config vs (b) graceful-`unavailable` decision, then ADR + task.
- t2 (Minor): **Finding 2** — JS analyzers report `unavailable` not `error` on no-JS
  targets (shares the error-vs-unavailable contract ADR with t1).
- t3 (Minor): **Finding 1** — schemathesis swallowed-exception → `execution-error` finding.
- Backlog: **Finding 5** — semgrep ruleset breadth (ADR-0016 revisit).
