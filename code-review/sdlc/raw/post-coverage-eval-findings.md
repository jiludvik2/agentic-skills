# Post-coverage-eval findings (2026-05-30, PyGoat Python dogfood)

Source: `polyreview run --depth full` against OWASP PyGoat after epic-analyzer-polish s0.
Full assessment: `sdlc/docs/qa/analyzer-coverage/results/2026-05-30-pygoat-python-coverage.md`.
Candidates for the next analyzer-polish epic / story. Severity in the author's estimate.

## G1 (Important) — jscpd scans non-JS files despite documented JS-only scope
On PyGoat, jscpd's 96 findings were `.html:71, .css:18, .py:3, .js:2, .md:1`. The adapter
(`code_review/adapters/jscpd.py`) passes no `--format`, so jscpd auto-detects and scans every
language. s0-fix1's `has_js_files` guard only decides run-vs-skip (skips when NO js present);
once it runs (any js present, e.g. PyGoat's static JS), it duplicate-scans HTML/CSS/Python too.
This contradicts the intentional JS-only scoping in `lang_select._JS_ADAPTERS` and capabilities
`languages:[javascript,typescript]`. Options: (a) pass `--format javascript,typescript,...` to
restrict jscpd to the JS family; (b) accept multi-language duplication as a feature and correct
the JS-only scoping claim (capabilities + lang_select + ADR-0019). Decide intent, then align.

## G2 (Important) — vulture false-positives on Django
167 vulture findings on PyGoat, dominated by Django framework patterns it can't see usage for:
`unused class 'ChallengeAdmin'` (admin registration), `unused variable 'list_display'/'search_fields'`
(ModelAdmin/Meta attrs), 25 findings in `settings.py` (module-level Django settings consumed by the
framework). All at 60% confidence. As shipped, dead-code signal on any Django/framework project is
mostly noise. Options: raise the default vulture `--min-confidence`, ship a Django-aware ignore list,
or document the framework-FP caveat. Needs a precision target to tune against (see G5).

## G3 (Minor) — per-analyzer duration telemetry always 0.00s
Every analyzer in the consolidated output reports `duration_s: 0.00`, and there is no top-level
duration field. The `analyzers: N | findings: M | duration: T s` summary also printed `0.00s`.
Timing capture (likely in `_run_analyzers` / the AnalyzerOutput.duration_s plumbing) is not recording.

## G4 (known, F5 deferred) — semgrep thinness confirmed
4 semgrep findings on PyGoat, all overlapping bandit (dangerous-eval, subprocess-shell-true); no XSS,
SSRF, or Django-specific coverage. Already tracked as the deferred candidate story s1 (semgrep ruleset
breadth / ADR-0016 revisit) on epic-analyzer-polish.

## G5 (method gap) — maintainability scanners have no documented oracle
vulture/radon/cohesion/pydeps cannot be assessed for precision against a vulnerability app (no
ground-truth quality catalogue). To assess them we need a dedicated benchmark: a repo with known/
documented complexity hotspots, real dead code, and known coupling — or synthetic fixtures with a
labelled expected-findings set (the analyzer-coverage QA harness could be extended for this).

## Validated (no action) — s0 fixes confirmed on a real repo
- bandit: 58 SAST findings on PyGoat (pre-s0-t0: crash → 0). s0-t0 ✓
- eslint → `unavailable` ("no ESLint config"); knip → `unavailable` ("no package.json"). s0-t1/t2 ✓
- Security coverage strong for code-pattern OWASP categories + deps (trivy 102 CVEs) + secrets.
