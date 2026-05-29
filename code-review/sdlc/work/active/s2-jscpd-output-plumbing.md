---
id: s2-jscpd-output-plumbing
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [jscpd, duplication, adapter, ga-readiness]
---

# s2 — jscpd output plumbing

## Summary

The jscpd adapter runs `jscpd --reporters json --output /dev/stdout` and reads
stdout. jscpd treats `--output` as a **directory** and calls `mkdir` on it,
failing with `EEXIST: ... mkdir '/dev/stdout'` (FINDINGS.md F2). Reproduced on
the **pinned** jscpd 4.0.5 — not version drift. jscpd *detects the duplication
correctly* when `--output` is a real directory; only the stdout plumbing is
broken.

Fix: write the report to a `TemporaryDirectory` and read
`<dir>/jscpd-report.json`, exactly as the trivy and gitleaks adapters already do
for their file-based reporters.

## Use case

- **As a** host operator running duplication analysis
- **I want** `polyreview --review maintainability` to return jscpd findings
- **so that** copy-paste duplication is actually reported instead of erroring.

## Acceptance criteria

### Scenario: jscpd reads its report from a temp directory
- **Given** the jscpd adapter after this story
- **When** it runs
- **Then** it passes `--output <TemporaryDirectory>` (not `/dev/stdout`) and
  parses `<dir>/jscpd-report.json`, cleaning up the temp dir afterward.

### Scenario: duplication is reported
- **Given** the analyzer-coverage smoke test
- **When** the jscpd case runs against `fixtures/js/src/clone_a.ts` +
  `clone_b.ts`
- **Then** jscpd returns ≥1 duplication finding and the case passes.

### Scenario: unit coverage
- **Given** the test suite
- **When** the jscpd adapter is tested
- **Then** a unit test exercises the temp-dir-write + report-read path (mirroring
  the existing trivy/gitleaks adapter tests).
