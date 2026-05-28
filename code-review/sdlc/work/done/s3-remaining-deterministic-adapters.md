---
id: s3-remaining-deterministic-adapters
kind: story
project: code-review
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26  # sandbox compatibility: per-adapter cache flags + vendored Node binaries
---

# s3 — Remaining deterministic adapters (Python + JS/TS coverage)

## Summary

Extend adapter coverage from the s0 reference pair (Semgrep, Radon) to the full deterministic set needed for Python and React/Next.js review: Bandit, gitleaks, Trivy, jscpd, vulture, knip, dependency-cruiser, ESLint with sonarjs, pydeps, cohesion. Includes SARIF normalisation shims for tools whose native output isn't SARIF.

Each new adapter shows up automatically in the skill's `capabilities.json` analyzer registry (s1) and in the `--capabilities` runtime check. Every adapter is configured to run cleanly inside the Claude Code sandbox: caches stay inside CWD, JS adapters invoke vendored Node binaries rather than fetching from the npm registry, and any tool that defaults to a network-fetch behaviour is wired to offline mode using pre-fetched local data (see architecture §16.3 for the per-adapter table).

## Use Case

- **As a** SDLC operator reviewing a polyglot repo (Python backend + Next.js frontend)
- **I want to** invoke a single CLI command that runs security, secrets, duplication, dead code, complexity, coupling, and cohesion analyzers across both languages, producing one consolidated SARIF report
- **so that** the sub-agent gets one input document instead of orchestrating nine tools individually, and so that the Reviewer skill is genuinely useful for this repo's actual stack

## Acceptance Criteria

### Scenario: Each new adapter implements the Analyzer Protocol from s0

- **Given** the s0 `Analyzer` Protocol
- **When** I inspect each of `BanditAdapter`, `GitleaksAdapter`, `TrivyAdapter`, `JscpdAdapter`, `VultureAdapter`, `KnipAdapter`, `DependencyCruiserAdapter`, `EslintAdapter`, `PydepsAdapter`, `CohesionAdapter`
- **Then** each one conforms to the Protocol with no changes required to the Protocol itself; the seam stays stable

### Scenario: Adapters that emit SARIF natively pass it through

- **Given** Bandit, gitleaks, Trivy, and ESLint (configured with `--format sarif` or equivalent)
- **When** their adapters run against fixture repos with known issues
- **Then** each adapter's `AnalyzerOutput.sarif` validates against SARIF 2.1.0 and contains the expected finding for that fixture

### Scenario: Adapters whose native output is not SARIF emit a normalised SARIF report

- **Given** jscpd (JSON output), vulture (text/JSON), knip (JSON), pydeps (DOT/JSON), cohesion (text), dependency-cruiser (JSON)
- **When** their adapters run against fixture repos
- **Then** each adapter's `AnalyzerOutput.sarif` validates against SARIF 2.1.0; the `tool.driver.name` field identifies the original tool; each `result` carries `ruleId` of the form `<toolname>.<category>`; locations are populated from the native output

### Scenario: Metrics-producing adapters populate MetricSet alongside SARIF

- **Given** pydeps (coupling), cohesion (LCOM4), Radon already in s0 (complexity)
- **When** they run
- **Then** each populates `AnalyzerOutput.metrics` with the appropriate per-file or per-class measurements; the consolidated `MetricSet` reaching the aggregator (s2) contains all axes

### Scenario: JS/TS analyzers handle a Next.js project structure

- **Given** a fixture Next.js project with `app/`, `pages/`, `components/`, and `lib/` directories
- **When** the ESLint and dependency-cruiser adapters run
- **Then** ESLint loads the project's `eslint.config.js` if present (otherwise a skill default), reports findings against TypeScript and JSX files, and dependency-cruiser reports the dependency graph with no false-positive cycle errors caused by Next.js framework imports

### Scenario: JS/TS adapters invoke vendored binaries, not the npm registry

- **Given** the skill has been set up (`./scripts/setup.sh` has run once, populating `.claude/skills/code-review/node_modules/`)
- **When** the ESLint, dependency-cruiser, jscpd, or knip adapter runs
- **Then** the subprocess invocation is `node .claude/skills/code-review/node_modules/.bin/<tool> <args>`, not `npx <tool> <args>`; the resolved binary path is recorded in the adapter's debug output; no network call is made to the npm registry during the run
- **and Given** the skill is invoked before `setup.sh` has run (i.e. `node_modules/` is absent)
- **Then** `--capabilities` reports each JS adapter as `status: unavailable` with an error message pointing to `setup.sh`

### Scenario: Trivy runs in offline mode against a pre-fetched database

- **Given** the skill has been set up (Trivy's vulnerability DB pre-fetched into `.claude/skills/code-review/cache/trivy-db/`)
- **When** the Trivy adapter runs
- **Then** Trivy is invoked with `--cache-dir .claude/skills/code-review/cache/trivy-db --skip-db-update --offline-scan`; no network call is made during the scan; findings against the pre-fetched DB appear correctly
- **and Given** the cache directory is absent or empty
- **Then** `--capabilities` reports `trivy.status: unavailable` with an error pointing to the setup script

### Scenario: Semgrep runs without writing outside CWD

- **Given** the Semgrep adapter is configured
- **When** the adapter runs
- **Then** the subprocess environment includes `SEMGREP_USER_DATA_FOLDER=.claude/skills/code-review/cache/semgrep` and `--metrics off`; Semgrep does not attempt to write to `~/.semgrep_logs/` or `~/.semgrep/`; rule packs are loaded from local files pre-fetched at setup, not from the Semgrep registry

### Scenario: No adapter writes outside the project's CWD

- **Given** any adapter from this story is running
- **When** I monitor filesystem writes during the run (e.g. via `inotifywait` on Linux or `fs_usage` on macOS)
- **Then** every write target is contained within the project's CWD subtree; no writes to `~/`, `/tmp`, `/var`, or any other path outside CWD are observed. This is verified by the sandbox-compatibility test in `test_sandbox_compatibility.py`.

### Scenario: Operator can disable any adapter via the skill's code-review.toml

- **Given** `code-review.toml` lists `disabled_analyzers = ["trivy"]`
- **When** the CLI is invoked with `--analyzer trivy`
- **Then** the CLI exits with a clear error naming the disabled analyzer; alternatively, if no `--analyzer` flags are passed (use defaults from `capabilities.json`'s default analyzer set), disabled analyzers are silently excluded with a one-line note in the consolidated output

### Scenario: Per-language adapter selection works without explicit listing

- **Given** the CLI is invoked with `--scope per-task` and no explicit `--analyzer` flags
- **When** the CLI introspects the diff
- **Then** it selects the appropriate adapter set per touched file's language (Python files trigger Bandit/Radon/vulture; JS/TS triggers ESLint/jscpd/knip; both languages trigger gitleaks and Trivy); the selection is recorded in the consolidated output's `analyzers_run` field

### Scenario: Adapter timeouts are configurable and bounded

- **Given** the s1 capabilities registry declares default timeouts per analyzer (Bandit 60s, Semgrep 120s, Trivy 180s, ESLint 90s, others 60-120s)
- **When** an adapter exceeds its timeout
- **Then** the CLI kills the subprocess, records `analyzers.<name>.status == "timeout"` with the configured limit, and continues running the remaining analyzers; the consolidated output still validates against the s1 response schema

## Test specification

- **Per-adapter integration test** — each adapter gets its own test against a language-appropriate fixture with at least one known finding; assert SARIF/MetricSet correctness.
- **SARIF schema test** — all new adapters' outputs validated against the SARIF 2.1.0 JSON schema.
- **Normalisation shim test** — for each non-SARIF-native adapter, golden-file test from raw tool output → normalised SARIF.
- **Next.js fixture test** — fixture mimics `create-next-app` structure with one each of: an `app/` route, a `pages/` route, a `components/` file, an `api/` route; ESLint and dependency-cruiser produce expected output.
- **Vendored-binary test** — strace/dtrace the JS adapter subprocess; assert the executed binary path resolves under `node_modules/.bin/` (not `/usr/local/bin/npx` or similar); assert no DNS resolution for `registry.npmjs.org`.
- **Trivy offline test** — run the Trivy adapter with the network stack patched to fail any outbound connection; assert the run succeeds against the pre-fetched DB and reports the expected finding.
- **Semgrep cache-dir test** — set `HOME` to an empty temporary directory, run the Semgrep adapter; assert no writes to that directory; assert all Semgrep cache files land under `.claude/skills/code-review/cache/semgrep/`.
- **No-writes-outside-CWD test** — generic test that runs every adapter in this story against a fixture while monitoring writes; asserts every write is contained in CWD subtree.
- **Setup-not-run test** — remove `node_modules/` and `cache/trivy-db/`, run `--capabilities`, assert the affected adapters report `unavailable` with helpful errors pointing to `setup.sh`.
- **Disabled-adapter test** — assert clear error on explicit invocation of disabled adapter; assert silent skip with note when defaulted.
- **Language-detection test** — diff with only Python files → only Python adapters selected; diff with both Python and TS files → all relevant adapters selected.
- **Timeout test** — adapter intentionally configured with a 1ms timeout against a fixture that takes longer; assert `status: "timeout"`, no crash, other adapters' results preserved.

## Out of scope (deferred to later stories)

- Contract testing adapters (Schemathesis, Pact) — those have different lifecycle constraints; see s4.
- Adapter version pinning / automatic updates — versions are pinned in `pyproject.toml` / `package.json` and updated manually.
- Custom rulesets per repo beyond what each adapter's standard config files support — config customisation already enabled by s2's `code-review.toml`.
- Snapshot or screenshot adapters (UI testing) — out of Reviewer scope, lives in the SDLC's snapshot-script convention instead.
- The `setup.sh` script implementation itself — this story specifies what adapters expect from `setup.sh` (pre-fetched DBs, `node_modules/` populated) and depends on it being present at runtime, but writing the script lives in s1's skill-packaging scope (it's part of getting the skill installable).
