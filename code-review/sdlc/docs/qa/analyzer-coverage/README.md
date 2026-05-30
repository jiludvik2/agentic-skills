---
id: qa-analyzer-coverage
kind: runbook
project: code-review
created: 2026-05-29
updated: 2026-05-29
verified-on: 2026-05-29
tags: [qa, analyzers, smoke-test]
---

# Analyzer-coverage smoke test

Exercises **every** analyzer in the `polyreview` registry end-to-end against
synthetic code that plants exactly the defect each analyzer is meant to find,
then asserts the analyzer ran and produced its expected signal (a SARIF finding,
or populated metrics for the metrics-only analyzers).

This is a **capability / integration** test — complementary to the unit tests in
`tests/`. It runs the real third-party binaries (semgrep, gitleaks, trivy, the
Node tools) and a live FastAPI server (for schemathesis), so it needs a fully
provisioned environment that the unit tests deliberately mock away.

## Layout

```
analyzer-coverage/
  scaffold_fixtures.sh   regenerates fixtures/ (planted defects, one per analyzer)
  run_smoke.py           the harness: runs all 13 analyzers, writes results
  contract-testing.toml  schemathesis target config (local FastAPI app)
  semgrep-rules/         legacy QA fixture ruleset (independent of the canonical
                         vendored set the harness now relies on — see below)
  fixtures/              synthetic targets (generated; safe to delete)
  results/
    <date>-results.md    machine-generated run record (overwritten each run)
    raw/<analyzer>.json   per-analyzer consolidated output
  FINDINGS.md            curated defects found by this test (hand-maintained)
```

## Analyzer → fixture map

| Analyzer | Fixture | Planted defect | Signal asserted |
|----------|---------|----------------|-----------------|
| bandit | `python/sec_vuln.py` | shell=True, md5, eval, pickle | ≥1 finding |
| semgrep | `python/sec_vuln.py` | eval, shell=True | ≥1 finding (local rules) |
| gitleaks | `python/secrets_leak.py` | AWS / GitHub / Slack creds | ≥1 finding |
| trivy | `deps/requirements.txt` | PyYAML 5.1, requests 2.19.0 CVEs | ≥1 finding |
| radon | `python/complex_fn.py` | high cyclomatic complexity | metrics `max_cc ≥ 10` |
| vulture | `python/dead_code.py` | unused import/func/class/var | ≥1 finding |
| cohesion | `python/low_cohesion.py` | `GrabBag` low-cohesion class | ≥1 finding |
| pydeps | `python/couplingpkg/` | `hub.py` imports 12 siblings | coupling metrics |
| eslint | `js/lint_me.js` | no-unused-vars, no-debugger | ≥1 finding |
| knip | `js/` (entry `src/index.ts`) | unreachable files | ≥1 finding |
| jscpd | `js/src/clone_a,b.ts` | duplicated block | ≥1 finding |
| depcruiser | `js/src/cycle_a,b.ts` | circular import | ≥1 finding |
| schemathesis | `api/app.py` (live) | 200 body violates schema | ≥1 finding |

## Prerequisites

Run **outside** the sandbox (needs network for the Trivy DB and the
schemathesis HTTP loop; semgrep rules are now vendored, not downloaded — see
step 1). From the repo root (`code-review/`):

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
4. **Contract testing:** `fastapi` + `uvicorn` (already in the project venv).

## Run

```bash
uv run python sdlc/docs/qa/analyzer-coverage/run_smoke.py
```

Exit code 0 iff all 13 analyzers produce their expected signal. The harness sets
`POLYREVIEW_CACHE_DIR` (→ the skill's vendored `node_modules` + Trivy DB) and
`NODE_PATH` (so eslint resolves its SARIF formatter regardless of cwd), asserts
the vendored semgrep ruleset is already provisioned (by `setup.sh`), and manages
the FastAPI server lifecycle.

## Note on committing fixtures

`fixtures/` contains intentionally-insecure code and dummy secrets (well-known
example values, e.g. `AKIAIOSFODNN7EXAMPLE`). They are excluded from the
package's own lint/type/test runs (they live outside `code_review/` and
`tests/`). If the repo's own gitleaks/secret CI scans the whole tree, add an
allowlist entry for `sdlc/docs/qa/analyzer-coverage/fixtures/`.
