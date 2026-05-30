---
id: s2-t0-jscpd-tempdir-report
kind: task
project: code-review
status: active
parent: s2-jscpd-output-plumbing
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-30
updated: 2026-05-30
tags: [jscpd, duplication, adapter, tempdir]
---

# s2-t0 — jscpd reads its JSON report from a temp directory

## Outcome

The jscpd adapter writes its report to a `TemporaryDirectory` and parses
`<dir>/jscpd-report.json`, instead of `--output /dev/stdout` (which jscpd `mkdir`s
and fails on with `EEXIST`). Mirrors the file-based-reporter pattern the trivy and
gitleaks adapters already use. Single coherent adapter change; implements all three
s2-story scenarios. No dependency on other epic stories.

## Acceptance criteria

(The s2-story scenarios are the contract; restated as the per-task gate.)

### Scenario: report read from a temp dir
- **Given** the jscpd adapter after this task
- **When** it runs
- **Then** it passes `--output <TemporaryDirectory>` (not `/dev/stdout`), parses
  `<dir>/jscpd-report.json`, and removes the temp dir afterward.

### Scenario: duplication is reported (smoke)
- **Given** the analyzer-coverage smoke test
- **When** the jscpd case runs against `fixtures/js/src/clone_a.ts` + `clone_b.ts`
- **Then** jscpd returns ≥1 duplication finding and the case passes.

### Scenario: unit coverage
- **Given** the test suite
- **When** the jscpd adapter is tested
- **Then** a unit test exercises the temp-dir-write + report-read path, mirroring
  the existing trivy/gitleaks adapter tests.

## Test specification

Write first, confirm red, then implement. Extend `tests/test_adapters/test_jscpd.py`
(or create it, modelled on `test_trivy.py`/`test_gitleaks.py`):

1. `test_jscpd_writes_report_to_tempdir_and_parses_it` (unit): patch the subprocess
   runner to drop a `jscpd-report.json` into whatever `--output` dir the adapter
   passes; assert the adapter (a) passes a real directory as `--output`, not
   `/dev/stdout`, (b) parses the report into findings, (c) leaves no temp dir
   behind. Mirror the existing trivy/gitleaks temp-dir test structure.
2. `test_jscpd_integration_detects_duplication` (`@pytest.mark.integration`, skip if
   jscpd not vendored): run the real adapter against the `clone_a.ts`/`clone_b.ts`
   fixtures; assert ≥1 duplication finding and `status=ok`.

## Notes

- jscpd detection itself is correct on the pinned 4.0.5 — only the stdout plumbing
  is broken; do not bump the pin.
- The smoke harness (`sdlc/docs/qa/analyzer-coverage/run_smoke.py`) jscpd case
  should pass unchanged once the adapter is fixed; confirm it goes green.
