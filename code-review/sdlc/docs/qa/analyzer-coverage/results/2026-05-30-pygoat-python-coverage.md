# Coverage assessment — polyreview vs OWASP PyGoat (Python)

**Date:** 2026-05-30
**Target:** OWASP PyGoat (`github.com/adeyosemanputra/pygoat`, shallow clone), 52 Python files,
deliberately-vulnerable Django app with documented OWASP Top-10 labs (2021: A1/A2/A3/A7/A8;
2017: SQL, CMD, XSS, XXE, SSRF, BrokenAccess, BrokenAuth, DataExp, sec_mis, insec_des, A9).
**Command:** `polyreview run --depth full --target <pygoat>` (12 analyzers; schemathesis excluded —
it is story-level/API-only). **Total: 520 findings.**
**Purpose:** post-`epic-analyzer-polish` re-run — validate the s0 fixes on a real repo and assess
per-issue-type coverage against the repo's documented vulnerability catalogue.

## Per-scanner results

| Analyzer | Issue type | Findings | Assessment |
|---|---|---|---|
| **bandit** | SAST (security) | **58** | **Strong** — was a crash→0 before s0-t0; now lands on the documented lab files |
| **trivy** | dependency CVEs | **133** (102 unique) | **Strong** — maps to the documented vulnerable `requirements.txt` |
| **gitleaks** | secrets | 10 | Good — JWTs + API keys in `views.py`, `a7.js`, `a9.js` |
| **semgrep** | SAST (security) | 4 | **Thin** — all overlap bandit (dangerous-eval, subprocess-shell); known (ADR-0016, F5) |
| **vulture** | dead code | 167 | **Noisy** — dominated by Django framework false-positives (60% confidence) |
| **jscpd** | duplication | 96 | **Scope leak** — scans `.html`/`.css`/`.py`, not just JS (see Defects) |
| **cohesion** | cohesion | 52 | Unverified — no documented oracle in a vuln app |
| **radon** | complexity | 0 findings / **53-file metrics** | Reports via the metrics channel, not SARIF findings — working as designed |
| **pydeps** | coupling | 0 | Ran; no circular deps in PyGoat |
| **depcruiser** | JS coupling | 0 | Ran (not JS-skipped); n/a on Python |
| **eslint** | JS lint | **unavailable** | s0-t1 ✓ — "no ESLint config found" (clean skip, not error) |
| **knip** | JS dead-code | **unavailable** | s0-t2 ✓ — "no package.json" (clean skip, not error) |

## Coverage vs PyGoat's documented OWASP labs

### Covered (SAST code-patterns + dependencies + secrets)

- **A3 Injection** — SQL (`bandit B608`), command (`B602`/`B603`/`B404` + semgrep `subprocess-shell-true`),
  eval (`B307` + semgrep `dangerous-eval`). Findings land in `introduction/views.py`, `mitre.py`,
  `dockerized_labs/*` — the actual lab files. ✓✓
- **A2 Cryptographic Failures** — weak hash (`B324`), insecure randomness (`B311`), hardcoded
  passwords/secrets (`B105`/`B106` ×15) + gitleaks. ✓✓
- **A8 Software/Data Integrity (insecure deserialization)** — pickle (`B301`/`B403`), `yaml.load`
  (`B506`); the `PyYAML==5.1` enabling it is also flagged by trivy. ✓
- **XXE** — XML parsers (`B405`/`B406`/`B409`/`B317`/`B319`). ✓
- **A6 Vulnerable & Outdated Components** — trivy: 102 unique CVEs across the documented vulnerable
  `requirements.txt` (Django 4.2, PyYAML 5.1, Werkzeug 2.1.2, urllib3 1.26.9, PyJWT 2.4.0, …). ✓✓
- **Security Misconfiguration (partial)** — flask debug (`B201`), bind-all-interfaces (`B104`),
  request-without-timeout (`B113`). ✓ partial
- **Secrets / sensitive-data exposure** — gitleaks (generic-api-key ×8, jwt ×2). ✓

### Not covered — by design, not scanner defects

These documented labs are **logic / runtime / design** vulnerabilities outside static-analysis reach;
they require DAST, authenticated crawling, or manual review:

- **A1 Broken Access Control** — authorization logic.
- **A10 SSRF** — needs data-flow / runtime.
- **XSS (template)** — Django auto-escape / `mark_safe` misuse; would need targeted semgrep Django
  rules, which the thin vendored ruleset lacks.
- **A4 Insecure Design** — architectural.
- **A7 Authentication Failures (logic)** — partial only (hardcoded creds caught; session/flow not).
- **A9 Logging & Monitoring Failures** — absence-of-control, not a code pattern.

## Headline

1. **The `epic-analyzer-polish` s0 fixes are validated on a real repo.** Bandit now produces 58 SAST
   findings on a Python vuln app (pre-s0-t0 it crashed on its progress-bar stdout → 0). eslint and knip
   skip cleanly as `unavailable` instead of polluting the run with red errors.
2. **Security coverage is strong for the code-pattern OWASP categories** (injection, crypto,
   deserialization, XXE) plus vulnerable dependencies and secrets. The uncovered categories are
   fundamentally beyond SAST — expected.
3. **Three quality/precision gaps surfaced** (see the companion raw capture): jscpd scans non-JS files
   despite its documented JS-only scope; vulture is dominated by Django false-positives; per-analyzer
   duration telemetry reports `0.00s`.

## Defects / gaps (captured to `sdlc/raw/post-coverage-eval-findings.md`)

- **G1 (Important) — jscpd scans non-JS files.** 96 findings = `.html:71, .css:18, .py:3, .js:2`. The
  adapter passes no `--format`, so once it runs (any JS present) it scans the whole tree, contradicting
  the documented JS-only scope (`lang_select._JS_ADAPTERS`, capabilities `languages:[js,ts]`). s0-fix1's
  guard only gates run-vs-skip, not the scan scope.
- **G2 (Important) — vulture Django false-positives.** 167 findings dominated by framework patterns
  (admin classes, Meta/`list_display` attrs, `settings.py` vars) at 60% confidence. Needs a confidence
  floor and/or Django-aware ignores to be trustworthy.
- **G3 (Minor) — duration telemetry broken.** Every analyzer reports `duration_s: 0.00`.
- **G4 (known, F5) — semgrep thinness.** 4 findings, all overlapping bandit; no XSS/SSRF/Django rules.
- **G5 (method) — maintainability scanners lack a documented oracle.** vulture/radon/cohesion/pydeps
  precision cannot be judged against a vuln app; a dedicated quality benchmark repo is needed.
