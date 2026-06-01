# Output-capture audit — deterministic adapters (s2-t1)

**Date:** 2026-06-01 · **Epic:** `epic-analyzer-correctness` · **Story:** `s2-adapter-output-capture-audit`

## Why

Under the thin-runner raw-capture contract (ADR-0020) the bundle carries each tool's
**verbatim stdout**, and a consumer (the QA oracle or the reviewing agent) reads findings
from `outputs[].stdout`. Any adapter whose genuine findings land on **stderr** or in an
**unread file** therefore reads as *zero signal* — a silent false-negative. s2-t0 caught
exactly this in `gitleaks` (10 real leaks on pygoat, captured stdout 0 B). This audit
confirms every other deterministic adapter lands its findings in stdout, and records the
guard that keeps it that way.

## Audit table

Channel = where the tool emits findings; "→ stdout?" = whether the adapter ensures they
reach captured `outputs[].stdout`. All 13 registry adapters (`code_review/adapters/__init__.py`).

| Adapter | Invocation (findings flag) | Native channel | → stdout? | Mechanism / note |
|---|---|---|---|---|
| bandit | `python -m bandit --quiet --format json -r` | stdout (JSON) | ✅ | `--format json` → stdout; `--quiet` suppresses the log/progress (F3) |
| semgrep | `semgrep --sarif --config …` | stdout (SARIF) | ✅ | `--sarif` → stdout; log/settings redirected to a `$TMPDIR` tempdir via env |
| gitleaks | `gitleaks detect … --report-format json --report-path <tmp>` | **off-argv file** | ✅ | **s2-t0 fix:** report written to a `$TMPDIR` tempfile, read back onto stdout. Was stderr-banner-only → silent FN |
| trivy | `trivy fs --format sarif …` | stdout (SARIF) | ✅ | native stdout (no `--output`); logs to stderr |
| radon | `python -m radon cc --json` | stdout (JSON) | ✅ | `cc --json` → stdout |
| vulture | `python -m vulture` | stdout (text) | ✅ | `file:line: unused …` lines on stdout; oracle = `count_text_lines` |
| pydeps | `python -m pydeps --show-deps --no-output --noshow` | stdout (JSON) | ✅ | `--show-deps` → stdout; `--no-output/--noshow` suppress the `.svg` render only |
| cohesion | `python -m cohesion -d/-f` | stdout (text) | ✅ | per-class report on stdout |
| eslint | `node eslint --format <sarif-formatter>` | stdout (SARIF) | ✅ | SARIF formatter → stdout; NODE_PATH exported for formatter resolution |
| jscpd | `node jscpd --reporters json --output <tmpdir>` | **file** | ✅ | tool has no stdout-JSON mode → report dir read back onto stdout (the pattern gitleaks now mirrors); missing-report-on-OK → error |
| knip | `node knip --reporter json` | stdout (JSON) | ✅ | `--reporter json` → stdout |
| depcruiser | `node depcruise --output-type json` | stdout (JSON) | ✅ | config in a `$TMPDIR` tempfile; graph → stdout |
| jscomplexity | `node eslint --no-config-lookup --config <tmp> --format <sarif>` | stdout (SARIF) | ✅ | ESLint `complexity` rule @ threshold 0 → SARIF on stdout (same channel as eslint) |

## Findings

- **gitleaks** — the sole stdout-capture defect. **Fixed in s2-t0** (off-argv JSON
  report read-back). No other adapter shares the bug.
- **No silent siblings.** Two adapters legitimately route findings through a file
  (`jscpd`, and now `gitleaks`) because the tool has no stdout-JSON mode; both read the
  file back onto stdout and flip a missing-report-on-OK to `error` (an empty stdout would
  read as "found nothing" and mask the silence). The other eleven write findings to stdout
  directly. No sibling defect was found, so no `s2-t1-fixN-*` task was filed.
- **Coverage gap closed.** `jscomplexity` was in the registry but absent from the QA
  `run_smoke.py` harness (its only positive-signal coverage was its adapter integration
  test). Added a harness CASE (`count_sarif_results` on the JS fixture; verified ≥1).

## Regression guard

`tests/test_analyzer_output_capture_coverage.py` (runs in CI; no toolchain needed):

1. **Coverage** — every deterministic adapter in `REGISTRY` must have a positive-signal
   CASE in `run_smoke.py`. The harness's oracles parse `stdout` exclusively, so an adapter
   that emitted findings to stderr / an unread file would count zero against its case and
   turn the harness red. A new adapter added without a case fails this test outright.
2. **No re-parking** — `KNOWN_DEFERRED` may carry no xfail justified by a stdout/output-capture
   reason (that is exactly how the gitleaks FN hid). `KNOWN_DEFERRED` is currently empty.

Together with the per-adapter integration assertions (each asserts ≥1 real signal parsed
from `stdout`, not `status == ok` alone) this makes the gitleaks class of silent
false-negative hard to reintroduce. See also `FINDINGS.md` F15 (RESOLVED).
