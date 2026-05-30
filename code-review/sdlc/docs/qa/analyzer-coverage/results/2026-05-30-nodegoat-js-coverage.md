# Coverage assessment — polyreview vs OWASP NodeGoat (JavaScript)

**Date:** 2026-05-30
**Target:** OWASP NodeGoat (`github.com/OWASP/NodeGoat`, shallow clone), 50 JS files, Express app
with the OWASP Top 10 for Node.js planted in app code (documented tutorial pages
`app/views/tutorial/a1.html`–`a10.html`; README: "Look for comments in the source code").
`package.json` + `package-lock.json` present; **no eslint config** (uses legacy `.jshintrc`).
**Command:** `polyreview run --depth full --target <nodegoat>` (12 analyzers; schemathesis excluded).
**Total: 184 findings.** Companion to the PyGoat (Python) assessment of the same date.

## Per-scanner results

| Analyzer | Issue type | Findings | Assessment |
|---|---|---|---|
| **trivy** | dependency CVEs | **76** | **Strong** — reads `package-lock.json` (CVE-2021-44906, CVE-2020-7598, …) |
| **knip** | dead code | 31 | **Noisy** — flags `Gruntfile.js`, `config/env/*.js`, entrypoints as unused (FP; needs knip config) |
| **jscpd** | duplication | 74 | **Scope leak** — 68 of 74 are `.html` tutorial pages; only 5 real `.js` (see G1) |
| **gitleaks** | secrets | 3 | Good — private key `artifacts/cert/server.key`, config secrets |
| **semgrep** | SAST | **0** | **Zero JS coverage** — vendored ruleset is Python-first (ADR-0016 / F5) |
| **eslint** | JS lint/quality | **unavailable** | s0-t1 ✓ (no flat config → clean skip) — but **no JS lint coverage** results |
| depcruiser | JS coupling | 0 | Ran; no config, no circular deps surfaced |
| bandit/vulture/radon/cohesion/pydeps | Python | 0 | n/a — Python-only tools on a JS repo (ran `ok`, empty) |

## Coverage vs NodeGoat's documented OWASP Top 10

### Covered

- **Vulnerable & outdated components** — trivy: 76 CVEs across the documented vulnerable
  `package-lock.json`. ✓✓
- **Secrets / sensitive data** — gitleaks: a committed private key and config-file secrets. ✓

### NOT covered — the headline JS gap

**Every first-party JS code vulnerability NodeGoat documents is missed** — injection (SQL/NoSQL/command),
XSS, CSRF, SSRF, broken access control, insecure deserialization, insecure direct object reference,
regex DoS, etc. There is **no working first-party JS SAST** in the suite:

- **semgrep → 0** — the vendored ruleset has no JS rules (Python-first, ADR-0016).
- **eslint → unavailable** — no flat config on this (typical un-migrated) project; and stock eslint is a
  style linter, not a security scanner, so even when it runs it would not catch these.
- **no bandit-equivalent for JS** — the Python SAST powerhouse has no JS counterpart.

So on a JS vuln app, polyreview catches vulnerable dependencies and secrets but **0% of first-party code
vulnerabilities** — a materially larger gap than on Python, where bandit (58 findings) provides real SAST.

## Headline

1. **The s0 fixes behave correctly on JS too** — eslint skips cleanly as `unavailable` (no flat config);
   no spurious red. But the *consequence* is that the JS lint/quality dimension produces nothing here.
2. **JS first-party SAST is effectively absent** (semgrep 0 + eslint unavailable + no bandit-for-JS).
   This is the single biggest coverage gap and should be the top priority for the next analyzer epic.
3. **G1 (jscpd non-JS scope leak) reconfirmed** on a second repo: 68/74 findings are HTML tutorial pages.
4. **knip is FP-heavy without project config** (flags build/config/entrypoint files as unused) — a JS
   analog to vulture's Django false-positives on PyGoat.

## Gaps (captured to `sdlc/raw/post-coverage-eval-findings.md`)

- **G6 (Important/strategic) — no working first-party JS SAST.** semgrep ships no JS rules and eslint is
  unavailable/non-security. Broaden semgrep's JS ruleset (extends F5 beyond "thin" to "absent for JS"),
  and/or add a JS security linter. The biggest single coverage gap found in this dogfood.
- **G7 (Important) — knip false-positives without config.** Entrypoints/build/config files reported as
  unused. Needs a knip config or entrypoint heuristics; analog to G2 (vulture/Django).
- **G1 reconfirmed** — jscpd scans HTML (68/74 here); see the PyGoat capture.
