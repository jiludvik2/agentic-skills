---
id: s0-analyzer-facade-and-two-adapters
kind: story
project: code-review
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26  # sandbox compatibility: CWD-only output
---

# s0 — Analyzer façade and two reference adapters

## Summary

Establish the `Analyzer` Protocol and canonical SARIF / MetricSet types, with Semgrep and Radon as the two reference adapter implementations. Ship a CLI (`python -m code_review.cli`) that runs configured analyzers against a diff and emits consolidated JSON to stdout or a file. This is the seam that determines whether the architecture holds; the sub-agent integration in s5 depends on it.

## Use Case

- **As a** developer building the Reviewer sub-agent's tool layer
- **I want to** define a single `Analyzer` Protocol that every deterministic scanner implements, plus a CLI that the sub-agent can shell out to
- **so that** adding a new analyzer in s3 (Bandit, gitleaks, etc.) is a single adapter class and a registry entry, and so that the sub-agent's invocation surface stays one command regardless of how many analyzers are configured

## Acceptance Criteria

### Scenario: Protocol is defined and importable

- **Given** I have the reviewer package installed
- **and Given** I import `code_review.contracts`
- **When** I inspect the `Analyzer` Protocol
- **Then** it declares `name: str`, an async `run(workspace, request) -> AnalyzerOutput` method, and the `AnalyzerOutput` dataclass carries SARIF (`dict`), optional `MetricSet`, `duration_s`, and `error: Optional[str]`

### Scenario: Semgrep adapter produces SARIF against a fixture repo

- **Given** a fixture repo at `tests/fixtures/python-with-known-issues/` containing files with at least one known Semgrep finding (e.g. `subprocess.run(shell=True)`)
- **and Given** Semgrep is installed and on `PATH`
- **When** I run `python -m code_review.cli --analyzer semgrep --target tests/fixtures/python-with-known-issues/`
- **Then** the command exits 0 and prints SARIF JSON to stdout with at least one `result` whose `ruleId` matches the known finding and whose `locations[].physicalLocation.artifactLocation.uri` matches the file path

### Scenario: Radon adapter produces a MetricSet

- **Given** the same fixture repo containing a function with cyclomatic complexity ≥ 10
- **When** I run `python -m code_review.cli --analyzer radon --target tests/fixtures/python-with-known-issues/`
- **Then** the command exits 0 and prints JSON to stdout containing a `MetricSet` with per-file cyclomatic complexity, maintainability index, and raw metrics; the known high-CC function appears with `cc >= 10`

### Scenario: CLI runs multiple analyzers concurrently and emits a single consolidated document

- **Given** both `semgrep` and `radon` adapters are registered
- **When** I run `python -m code_review.cli --analyzer semgrep --analyzer radon --target <fixture>`
- **Then** both analyzers run concurrently (via `asyncio.TaskGroup`), their outputs are returned together in one JSON document with `analyzers.semgrep` and `analyzers.radon` keyed entries, and overall wall-clock time is closer to `max(t_semgrep, t_radon)` than to `t_semgrep + t_radon`

### Scenario: CLI supports diff-scoped analysis

- **Given** a git repo with at least two commits, where the more recent commit added a file with a known Semgrep finding
- **When** I run `python -m code_review.cli --analyzer semgrep --target <repo> --diff HEAD~1..HEAD`
- **Then** the output contains only findings in files changed by that diff range; pre-existing findings in unchanged files do not appear

### Scenario: Adapters fail in isolation without crashing the CLI

- **Given** the Semgrep binary is not on `PATH`
- **and Given** the Radon adapter is configured and works
- **When** I run `python -m code_review.cli --analyzer semgrep --analyzer radon --target <repo>`
- **Then** the CLI exits with a non-zero status, the consolidated output contains `analyzers.semgrep.error` with a human-readable message identifying the missing dependency, `analyzers.radon` contains usable output, and no traceback is printed to stderr

### Scenario: Fake adapter can drive end-to-end tests without subprocesses

- **Given** the test suite includes a `FakeAnalyzer` implementing the Protocol that returns canned SARIF and metrics
- **When** I run `pytest tests/test_facade.py`
- **Then** every test passes without spawning any subprocess, and the canned output flows through the same CLI code path real adapters use

### Scenario: Output is writable to a file for sub-agent consumption

- **Given** the CLI is invoked with `--output .claude/skills/code-review/runs/<id>.json` (or any path inside the project's CWD)
- **When** the run completes
- **Then** the consolidated JSON is written to that path atomically (write-then-rename, with the `.tmp` sibling in the same directory as the final file so the rename never crosses filesystems or sandbox-writable regions), and stdout contains only a short summary line (`analyzers: N | findings: M | duration: T s`)

### Scenario: Output paths outside the project's working directory are rejected

- **Given** the CLI is invoked with `--output /tmp/review.json` or any path outside the project's CWD
- **When** the CLI validates its arguments
- **Then** the CLI exits non-zero with a clear error explaining that all writes must stay inside CWD for sandbox compatibility (the operator's Claude Code sandbox blocks writes elsewhere by default); the error suggests `.claude/skills/code-review/runs/<id>.json` as the canonical path

## Test specification

- **Protocol surface tests** — assert that `Analyzer`, `AnalyzerOutput`, `MetricSet` exist with the expected fields; assert that an adapter that doesn't conform fails type-checking via `typing.get_type_hints`.
- **Semgrep adapter integration test** — invoke against fixture, assert SARIF schema validity (using `jsonschema` against the SARIF 2.1.0 schema), assert at least one expected finding present.
- **Radon adapter integration test** — invoke against fixture, assert `MetricSet` shape, assert known high-CC function appears with expected score range.
- **Concurrent execution test** — measure wall-clock with both adapters configured against a fixture sized to give each adapter a measurable runtime; assert max(t_individual) is closer to total than sum(t_individual).
- **Diff-scoped test** — repo with planted findings in both changed and unchanged files; assert only changed-file findings appear when `--diff` is passed.
- **Error-handling unit test** — patch `asyncio.create_subprocess_exec` to raise `FileNotFoundError`, assert CLI exits non-zero and the consolidated output captures the error per-analyzer without raising.
- **Fake-adapter end-to-end test** — exercise the whole CLI path with `FakeAnalyzer` to prove the seam is in the right place.
- **Atomic write test** — invoke with `--output`, assert no partial-file state visible during write (write to `.tmp` in the same directory as the final file, rename atomically).
- **CWD-only output test** — invoke with `--output /tmp/x.json`, `--output ~/x.json`, and `--output /etc/x.json`; assert each is rejected with a non-zero exit and the error names sandbox compatibility as the reason.

## Out of scope (deferred to later stories)

- Skill packaging (`.claude/skills/code-review/`, `SKILL.md`, `capabilities.json`) — s1.
- Result aggregation across analyzers, deduplication, severity mapping — s2.
- Remaining deterministic adapters (Bandit, gitleaks, Trivy, jscpd, vulture, knip, dependency-cruiser, ESLint, pydeps, cohesion) — s3.
- Contract testing (Schemathesis, Pact) — s4.
- Sub-agent integration and LLM design review — s5.
