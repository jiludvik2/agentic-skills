---
id: s2-t0-gitleaks-json-report
kind: task
project: code-review
status: done
parent: s2-adapter-output-capture-audit
sources: [s2-adapter-output-capture-audit.md, fu-gitleaks-json-output-capture.md]
created: 2026-06-01
updated: 2026-06-01
tags: [analyzer, gitleaks, output-capture, security, sandbox]
---

# Task — gitleaks: emit structured findings into the bundle stdout

## Outcome

The gitleaks adapter captures its findings as machine-readable JSON in the bundle
`outputs[].stdout` — rule id, file, line, secret, fingerprint per leak — rather than
the current empty stdout + count-only stderr banner (`leaks found: N` with zero
per-finding detail, confirmed empirically on pygoat: stdout 0 B, stderr 130 B).

## Acceptance criteria

- gitleaks writes a JSON report to an **off-argv temp file** (`--report-format json
  --report-path <tempfile>`); the adapter reads it back and the JSON lands in the
  captured `stdout`. Sandbox-safe: a real temp file, **not** a `/dev/stdout` redirect
  (memory `code-review-dev-stdout-not-writable-under-sandbox`).
- The QA analyzer-coverage `gitleaks` case moves from **xfail → real pass**;
  `count_gitleaks` (bundle_oracle) asserts ≥1 against the parsed JSON.
- Exit-code handling unchanged (0 = clean, 1 = leaks present, both `ok`).
- Secret values: confirm the captured report does not newly *persist* secrets beyond
  the bundle's existing exposure (the bundle already carries findings by design); no
  secret leaks onto argv (the report path is a temp file, not the secret).

## Test specification (write first, confirm RED)

1. Integration: gitleaks against a fixture containing a known planted secret →
   assert ≥1 finding parsed from `outputs[].stdout` JSON (rule/file present).
   **RED today:** stdout empty (case is currently `KNOWN_DEFERRED`/xfail in
   `run_smoke.py`). Flip it to an asserting pass.
2. Unit: the adapter constructs `--report-format json --report-path <tmp>` off-argv
   and reads the file back into the capture; assert the argv shape + read-back path
   handling (no `/dev/stdout`).
3. Sandbox guard: the temp-file path is writable under the OS sandbox (the failure
   mode that cost s1-t1 / FINDINGS F2).

## Implementation notes

- `code_review/adapters/gitleaks.py`: today invokes `gitleaks detect --source <t>
  --no-git` with **no** report path and a comment arguing against one. This task
  **supersedes that decision** — empirically neither stdout nor stderr carries the
  findings, only a count. Follow the temp-file-report-read-back pattern the trivy/jscpd
  adapters use; check `capture.py` for an existing report-file capture helper before
  adding one.
- Update the adapter comment (lines 21-25) accordingly. If the no-report-path choice
  was recorded in an ADR, add a short superseding note.
- Remove the gitleaks entry from `run_smoke.py` `KNOWN_DEFERRED` once it passes.
- Gates: `.venv/bin/pytest`, `.venv/bin/ruff check .`, `.venv/bin/mypy code_review`.
