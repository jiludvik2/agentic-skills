---
id: epic-analyzer-polish
kind: epic
project: code-review
status: active
children:
  - s0-analyzer-adapter-robustness
sources: [post-ga-self-review-findings.md]
created: 2026-05-30
updated: 2026-05-30
tags: [analyzer, robustness, post-ga, sast]
---

# Epic — analyzer polish (post-GA)

## Why

A post-GA full-review dogfood (`polyreview run --depth full`) on two canonical
OWASP vuln apps — **PyGoat** (insecure Django) and **NodeGoat** (insecure Node) —
showed that polyreview's **dependency + secret scanning is strong** (trivy surfaced
133 / 76 real CVEs; gitleaks found real API keys, JWTs, a private key) but its
**first-party SAST is degraded on real-world repos**:

- **bandit crashes** parsing its own stdout (a Rich progress bar precedes the JSON) —
  the primary Python security scanner returned zero findings on a Python vuln app.
- **eslint crashes** (`exited 2`) on real JS projects that have no ESLint-9 flat
  config — the common case — producing zero findings on a JS app.
- **semgrep is thin** — 4 findings on PyGoat, 0 on NodeGoat (vendored ruleset is
  small and Python-first per ADR-0016).

Net: on a vuln app, polyreview catches known-CVE dependencies and leaked secrets but
misses most first-party code vulnerabilities. None of this was caught by the unit
tests or the clean-code self-review — these defects only manifest on real repos.

## Goal

Make the analyzer adapters robust against real-world repositories so first-party
SAST coverage is not silently lost, and establish a clear contract for "analyzer
cannot meaningfully run here" vs "analyzer failed unexpectedly."

## Stories

- **s0-analyzer-adapter-robustness** (active) — fix the bandit + eslint crashes,
  give the JS analyzers a graceful no-target skip, and stop schemathesis swallowing
  errors. Governed by ADR-0019 (the unavailable-vs-error contract).

## Deferred / candidate future stories

- **s1 — semgrep ruleset breadth** (F5): broaden SAST coverage (e.g. vendor
  `p/security-audit` / language packs) or document the limitation. An ADR-0016
  revisit; not scoped until the operator decides direction.

## Source

Compiled from `sdlc/raw/post-ga-self-review-findings.md` (findings F1–F5), itself
produced by the post-GA self-review + vuln-repo test drive on 2026-05-30.
