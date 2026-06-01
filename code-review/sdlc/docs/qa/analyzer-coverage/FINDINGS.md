---
id: qa-analyzer-coverage-findings
kind: runbook
project: code-review
created: 2026-05-29
updated: 2026-05-31
verified-on: 2026-05-31
tags: [qa, findings, ga-readiness]
sources: [sdlc/docs/qa/analyzer-coverage/run_smoke.py]
---

# Analyzer-coverage findings — 2026-05-29

Defects surfaced by the analyzer-coverage smoke test (`run_smoke.py`) and a
follow-up CLI/test-coverage pass. Severity uses the SDLC taxonomy (Critical /
Important / Minor). The smoke run scored **11/13 analyzers** (2 broken by real
defects). The follow-up pass added F8–F10: it ran the pytest suite with the Node
toolchain actually installed (exposing F8/F9) and audited CLI option/error
coverage (F10). Several findings bear directly on GA readiness.

The environment under test: macOS, Node 24.14.1, pinned Node tools
(knip 5.0.0, jscpd 4.0.5, dependency-cruiser 16.0.0, eslint 9), semgrep/gitleaks/
trivy on PATH, Trivy DB pre-fetched.

## Critical

### F1 — `depcruiser` does not run (pinned dep incompatible with Node ≥ 22)
`dependency-cruiser@16.0.0` does `import { R_OK } from "node:fs"`, which Node 24
rejects (`R_OK` is on `fs.constants`, not a named export of `node:fs`):

```
SyntaxError: The requested module 'node:fs' does not provide an export named 'R_OK'
  at .../dependency-cruiser/src/cli/utl/assert-file-existence.mjs:1
```

The TypeScript/JS coupling capability is dead on any modern Node. Fix: bump
dependency-cruiser to a version that imports `R_OK` from `node:fs/constants`
(≥ ~16.3) and pin it in a committed lockfile (see F5). The detection logic is
fine once it runs.

### F2 — `jscpd` adapter writes JSON to `/dev/stdout`, which jscpd `mkdir`s
The adapter runs `jscpd --reporters json --output /dev/stdout` and reads stdout.
jscpd treats `--output` as a **directory** and calls `mkdir` on it:

```
Error: EEXIST: file already exists, mkdir '/dev/stdout'
```

Reproduced on the **pinned** jscpd 4.0.5 — not a version-drift issue. jscpd
*detects the duplication correctly* when `--output` points at a real temp
directory (1 clone found); only the stdout plumbing is broken. Fix: write the
report to a `TemporaryDirectory` and read `<dir>/jscpd-report.json` (as the
trivy/gitleaks adapters already do), instead of `/dev/stdout`.

## Important

### F3 — `semgrep` has no working rule source out of the box — ✅ RESOLVED (s0, ADR-0016)
**Resolved 2026-05-29** by epic `analyzer-ga-hardening` story `s0-semgrep-rule-source`:
a security ruleset is now vendored in the skill bundle (`semgrep-rules/`) and
provisioned into `cache/semgrep/rules` by `setup.sh` (s0-t1); the adapter
resolves it through `cache_root()`, drops the broken `--config auto` + `--metrics
off` combo for a loud, actionable error, and keeps the load-bearing
`--x-ignore-semgrepignore-files` flag (s0-t2); end-to-end from a clean `setup.sh`
is proven and the smoke harness no longer self-provisions (s0-t3). Original
problem statement retained below for history.

Two compounding problems:
1. `scripts/setup.sh`'s prefetch step writes **0** semgrep rules
   (`cache/semgrep/rules` is never populated).
2. With no local cache the adapter falls back to `--config auto`, but it also
   passes `--metrics off`, and semgrep refuses the combination:
   `Cannot create auto config when metrics are off`.

Net: a fresh install produces **zero** semgrep findings (it errors). The adapter
logic is correct — this test passes semgrep by provisioning a local ruleset
(`semgrep-rules/` → cache), proving the `--config <dir>` path works. Fix: make
the prefetch actually vendor a semgrep ruleset, and/or repair the `auto`
fallback (drop `--metrics off` when falling back to `auto`, or fail loudly
instead of silently). Also: `--x-ignore-semgrepignore-files` is not a recognized
flag in the installed semgrep (warning only, non-fatal).

### F5 — No JS/TS toolchain manifest or lockfile in the repo
`setup.sh` logs `Node dependencies (skipped — no package.json/package-lock.json
yet)`. The four Node analyzers (eslint, knip, jscpd, depcruiser) are neither
vendored nor version-pinned anywhere except the `version` strings in
`capabilities.json`. Installing "latest" drifts from what the adapters assume
(knip's JSON schema changed — see F4; depcruiser/Node compat — see F1). The JS
toolchain is effectively unshippable until a committed `package.json` +
lockfile pins these versions and `setup.sh` vendors them.

### F8 — `eslint` adapter passes only under harness-specific conditions
The smoke harness originally reported eslint as a clean pass, but that was an
artefact of how the harness ran it (`NODE_PATH` set so `@microsoft/eslint-formatter-sarif`
resolves, **and** cwd inside the fixture where `eslint.config.js` lives). Run as
the adapter itself invokes it (e.g. `tests/test_adapters/test_eslint.py::
test_eslint_integration_detects_console_log`), it returns `status=error`:
- `ESLint couldn't find an eslint.config.(js|mjs|cjs) file` — flat-config
  discovery is relative to the process cwd, which the adapter doesn't control;
- the SARIF formatter only resolves because the harness sets `NODE_PATH` — the
  adapter passes a bare `--format @microsoft/eslint-formatter-sarif` with no
  guarantee it resolves from the run cwd.

In the real "review a JS project from its root" case eslint finds that project's
config, so this is a robustness gap rather than a hard F1/F2-style break — but
the adapter must guarantee formatter resolution (absolute path or `NODE_PATH`)
and the integration test must be runnable without harness scaffolding.

### F9 — CI green is masking three failing Node-analyzer integration tests
`test_depcruiser_integration`, `test_jscpd_integration`, and
`test_eslint_integration_detects_console_log` carry `@pytest.mark.skipif(binary
missing)`. Because CI never installs the Node toolchain (F5), **all three skip**,
so the suite reports green while the Node analyzers are effectively untested —
this is *why* F1/F2 were never caught by pytest. Provisioning the toolchain
locally flips all three skip→**fail** (F1, F2, F8 respectively). Fix: once F5
vendors the tools, CI must install them and these tests must **fail, not skip**
(drop the skipif, or gate it on a CI flag that is set once the toolchain lands).

## Minor

### F4 — `knip` adapter drops unused-*export* findings (schema mismatch)
The adapter reads `data["exports"]`, but knip 5.0.0's JSON report is
`{"files": [...], "issues": [{... "exports": [...] ...}]}` — exports are nested
under `issues[]`, not top-level. Top-level `data["files"]` (unused files) maps
correctly, so the analyzer still reports (4 unused-file findings here), but every
unused-*export* is silently lost. Fix: read exports from `issues[].exports`.

### F6 — `pydeps` high-fan-out finding under-counts imports
`hub.py` imports 12 siblings, but pydeps' resolved graph reports `fan_out = 5`
for it, below the `_HIGH_FAN_OUT_THRESHOLD = 10`, so no finding fires. The
coupling **metrics** populate correctly (the analyzer's primary output), so this
test asserts metrics rather than the threshold finding. Worth confirming the
fan-out threshold is reachable with realistic code, or the finding may rarely
fire in practice.

### F7 — README install section omits the external-analyzer requirement
A bare `pip install polyreview` ships only the Python analyzers; the Node tools
and gitleaks/trivy are silently unavailable. A drafted fix to `README.md`'s
Install section is staged in the working tree (pending operator sign-off).

### F10 — Three CLI error branches have no test coverage
The CLI option surface and most invalid-input paths are covered by the pytest
suite (`CliRunner`, mocked analyzers) — `--output` outside CWD, unknown
`--depth`, unknown `--review`, contradictory `--depth`, scope violations,
malformed/missing/invalid `--config`. But three error branches in `cli.py` have
**zero** tests: unknown `--analyzer <name>` ("unknown analyzer(s)"), explicitly
selecting a **disabled** analyzer ("analyzer(s) disabled in code-review.toml"),
and "no analyzers selected after filtering". Add `CliRunner` cases asserting
exit 1 + message for each.

## Passing cleanly (7)

`bandit` (8), `gitleaks` (1), `trivy` (8), `vulture` (22), `cohesion` (2),
`radon` (metrics, max_cc=13), `schemathesis` (1) — all produced their expected
signal with no caveats. `semgrep`, `knip`, `pydeps` pass with the caveats noted
above. **`eslint` is no longer counted clean** — it only passed under harness
scaffolding (see F8).

## 2026-05-31 — bundle-migration run (epic analyzer-thin-runner, story s5)

The s5 work re-pointed the harness off the deleted consolidated SARIF/metrics
schema onto the raw review bundle (ADR-0020) and added two precision coupling
oracles. The **first real end-to-end run after the migration** (it had only been
unit-tested) scored **0/15**, then **13/14** after the fixes below — i.e. the
migrated harness immediately caught a cluster of real regressions. Final state:
**13/14 pass, 1 xfail (gitleaks), 0 real failures**; both precision oracles
(pydeps-cycles, depcruiser-mocks) pass against the real binaries.

### F11 — harness invoked the CLI with the pre-`run`-subcommand shape (was 0/15)
The bundle migration (s1-t3) restructured the CLI into subcommands (`run`,
`install`, `uninstall`); analyzer execution moved under `run`. `run_smoke.py`
still called `python -m code_review.cli --analyzer …` (flat), which every case
rejected with `rc=2: No such command`. The harness had been unit-tested but never
re-run end-to-end, so this was invisible until now. **Fixed:** `_run_cli` prepends
`run`. *Lesson: harness/integration code needs one real run before its task closes
— unit-green ≠ harness-works.*

### F12 — trivy oracle parsed native JSON, but the adapter emits SARIF
The trivy adapter runs `trivy fs --format sarif`, so bundle stdout is SARIF, but
the oracle used `count_trivy` (native `{"Results":…}`) → 0 findings on a real
8-CVE scan. **Fixed:** trivy case now uses `count_sarif_results`.

### F13 — harness still invoked `schemathesis`, removed from the registry (ADR-0021)
The case errored `unknown analyzer(s): schemathesis`. **Fixed:** removed the
schemathesis case, `run_schemathesis()`, the FastAPI `fixtures/api/` target, and
`contract-testing.toml` from the harness.

### F14 — `couplingpkg` fixture emitted invalid Python, crashing cohesion
`scaffold_fixtures.sh` generated `VALUE_${i} = ${i}` with `seq -w` zero-padding →
`VALUE_03 = 03`, a `SyntaxError` (leading zeros in decimal ints). cohesion's AST
parse over the package raised, status=error. Latent since the couplingpkg fixture
was added; only surfaced now because cohesion is exercised over that tree.
**Fixed:** `VALUE_${i} = $((10#${i}))` (strip the pad; harmless to pydeps fan-out).

### F15 — `gitleaks` emits no JSON on stdout (RESOLVED — s2-t0, 2026-06-01)
The adapter ran `gitleaks detect --source X --no-git` with **no**
`--report-format json`, so findings printed to **stderr** in human format and
captured **stdout was empty** → any bundle consumer (oracle or agent) saw zero
findings even though gitleaks found the secret (stderr: `leaks found: 1`, exit 1).
A real shipping-adapter defect, exposed by the raw-capture model (the old facade
parsed it differently). **Fixed in s2-t0** (`epic-analyzer-correctness`): the
adapter now writes an off-argv JSON report (`--report-format json --report-path
<tempfile>`, sandbox-safe — not `/dev/stdout`) and splices it onto captured stdout
(the trivy/jscpd pattern). The harness `gitleaks` case moved xfail → real pass and
`KNOWN_DEFERRED` is now empty. The broader output-capture audit it motivated is
tracked as s2-t1. Verified end-to-end: `polyreview run --analyzer gitleaks` on
`python/secrets_leak.py` → bundle `outputs[].stdout` carries the JSON array,
`count_gitleaks` = 1 (slack-bot-token).

## GA-readiness implication

The original GA question was "is `polyreview` ready to publish?" This test says:
**the Python analyzers and schemathesis are solid, but the JS/TS toolchain is not
shippable** (F1, F2, F5, F8) and **semgrep is broken out of the box** (F3). A GA
that advertises TypeScript coverage and security scanning would mislead users
until F1–F3, F5, and F8 are fixed. Compounding this, **CI is green only because
the Node-analyzer integration tests skip** (F9) — so the test suite currently
provides false assurance for exactly the analyzers that are broken.
