---
id: qa-analyzer-coverage
kind: runbook
project: code-review
created: 2026-05-29
updated: 2026-05-31
verified-on: 2026-05-31
tags: [qa, analyzers, smoke-test]
---

# Analyzer-coverage smoke test

Exercises **every** analyzer in the `polyreview` registry end-to-end against
synthetic code that plants exactly the defect each analyzer is meant to find,
then asserts the analyzer ran (review-bundle status `ok`) and produced its
expected signal **in its raw native output**.

As of the thin-runner re-architecture (ADR-0020) the CLI emits a
`review-bundle.v1.json` — one raw per-tool capture (`stdout`/`stderr`/`exit_code`/
`status`), no consolidated SARIF/metrics layer — so the harness reads that bundle
and routes each tool's raw stdout through `bundle_oracle.py`, which knows each
tool's native output shape (SARIF for semgrep/eslint/trivy; native JSON for
bandit/gitleaks/knip/jscpd/pydeps/depcruiser; text for vulture/cohesion). Two
cases are **precision oracles**: they assert the *specific* planted coupling
defect (see the map below), so a tool that runs but silently stops detecting it
fails loudly.

This is a **capability / integration** test — complementary to the unit tests in
`tests/`. It runs the real third-party binaries (semgrep, gitleaks, trivy, the
Node tools), so it needs a fully provisioned environment that the unit tests
deliberately mock away.

## Layout

```
analyzer-coverage/
  scaffold_fixtures.sh   regenerates fixtures/ (planted defects, one per analyzer)
  run_smoke.py           the harness: runs all 14 analyzer cases, writes results
  bundle_oracle.py       pure per-tool signal extractors over a review bundle
                         (raw stdout → did the planted defect appear?), incl. the
                         two precision coupling oracles. Unit-tested in tests/.
  semgrep-rules/         legacy QA fixture ruleset (independent of the canonical
                         vendored set the harness now relies on — see below)
  fixtures/              synthetic targets (generated; safe to delete)
  results/
    <date>-results.md    machine-generated run record (overwritten each run)
    raw/<case>.json       per-case raw review bundle (review-bundle.v1.json:
                          per-tool raw stdout/stderr/exit_code/status — ADR-0020)
  FINDINGS.md            curated defects found by this test (hand-maintained)
```

## Analyzer → fixture map

Each row reads the named tool's **raw native** stdout from the review bundle via
`bundle_oracle`. "Signal asserted" is what the oracle checks; the two **precision**
rows assert the *specific* planted coupling defect, not just ≥1.

| Case | Fixture | Planted defect | Signal asserted (from raw output) |
|------|---------|----------------|-----------------------------------|
| bandit | `python/sec_vuln.py` | shell=True, md5, eval, pickle | ≥1 result in bandit JSON |
| semgrep | `python/sec_vuln.py` | eval, shell=True | ≥1 SARIF result (local rules) |
| gitleaks | `python/secrets_leak.py` | AWS / GitHub / Slack creds | ≥1 finding in gitleaks JSON |
| trivy | `deps/requirements.txt` | PyYAML 5.1, requests 2.19.0 CVEs | ≥1 SARIF result (`--format sarif`) |
| radon | `python/complex_fn.py` | high cyclomatic complexity | `max_cc ≥ 10` from `radon cc --json` |
| vulture | `python/dead_code.py` | unused import/func/class/var | ≥1 report line |
| cohesion | `python/low_cohesion.py` | `GrabBag` low-cohesion class | ≥1 report line |
| pydeps | `python/couplingpkg/` | `hub.py` imports 12 siblings | coupling graph computed (fan-out ≥ 1) |
| **pydeps-cycles** | `python/cyclepkg/` | labelled `a → b → a` import cycle | **precision:** mutual back-edge `a↔b` present in the dep graph |
| eslint | `js/lint_me.js` | no-unused-vars, no-debugger | ≥1 SARIF result |
| knip | `js/` (entry `src/index.ts`) | unreachable files | ≥1 unused file/issue |
| jscpd | `js/src/clone_a,b.ts` | duplicated block | ≥1 duplicate |
| depcruiser | `js/src/cycle_a,b.ts` | circular import | ≥1 `circular: true` edge |
| **depcruiser-mocks** | `js/src/app.ts` → `js/__mocks__/service.ts` | prod→`__mocks__` coupling | **precision:** edge from a non-mock source into `__mocks__/` present |

**xfail (known-deferred).** None currently. `KNOWN_DEFERRED` in `run_smoke.py` is the
authoritative list; xfail rows are reported but do **not** fail the run. The former
`gitleaks` xfail was resolved by s2-t0: the adapter now writes an off-argv JSON report
(`--report-format json --report-path <tempfile>`) and splices it onto captured stdout,
so the oracle counts the real findings (≥1).

## Prerequisites

Run **outside** the sandbox (the Trivy DB pre-fetch needs network; once cached,
the run itself is offline — semgrep rules are vendored, not downloaded). From the
repo root (`code-review/`):

1. **Python tooling + semgrep rules:** `./scripts/setup.sh` — installs Python
   deps and provisions the vendored semgrep ruleset into `cache/semgrep/rules`
   (ADR-0016). The harness asserts this cache is populated and no longer
   self-provisions; if you skip `setup.sh` it fails loud naming it.
2. **Node tooling** — the repo ships no `package.json`/lockfile (see FINDINGS
   #5), so install the *pinned* versions the adapters target into the cache:
   ```bash
   cd .claude/skills/code-review
   npm install --no-save eslint@9 knip@5.0.0 jscpd@4.0.5 \
       dependency-cruiser@16.0.0 @microsoft/eslint-formatter-sarif
   cd -
   ```
3. **Standalone binaries:** `brew install gitleaks trivy`, then pre-fetch the
   Trivy DB: `trivy fs --cache-dir .claude/skills/code-review/cache/trivy-db --download-db-only`.

## Run

```bash
uv run python sdlc/docs/qa/analyzer-coverage/run_smoke.py
```

Exit code 0 iff every analyzer case produces its expected signal, **except**
known-deferred xfail cases (see `KNOWN_DEFERRED` in `run_smoke.py`) which are
reported but don't fail the run. The harness sets `POLYREVIEW_CACHE_DIR` (→ the
skill's vendored `node_modules` + Trivy DB) so the adapters resolve their vendored
tooling, and asserts the vendored semgrep ruleset is already provisioned (by
`setup.sh`).

## Note on committing fixtures

`fixtures/` contains intentionally-insecure code and dummy secrets (well-known
example values, e.g. `AKIAIOSFODNN7EXAMPLE`). They are excluded from the
package's own lint/type/test runs (they live outside `code_review/` and
`tests/`). If the repo's own gitleaks/secret CI scans the whole tree, add an
allowlist entry for `sdlc/docs/qa/analyzer-coverage/fixtures/`.
