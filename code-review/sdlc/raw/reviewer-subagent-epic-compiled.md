# Reviewer Sub-agent — Epic & Stories (Compiled)

Compiled view of the epic and all six stories. Each section preserves the original artefact unchanged. Individual files are authoritative; this compiled version is for review only.

---

---
id: epic-reviewer-subagent
kind: epic
project: sdlc
status: active
children:
  - s0-analyzer-facade-and-two-adapters
  - s1-reviewer-skill-and-capabilities
  - s2-aggregator-and-severity-mapping
  - s3-remaining-deterministic-adapters
  - s4-contract-testing-adapters
  - s5-subagent-integration-and-design-review
created: 2026-05-26
updated: 2026-05-26  # scope model: lite/standard/full replaces basic/full-reviewer split
tags: [reviewer, sarif, sdlc, ai-native, subagent]
---

# Epic: Reviewer Sub-agent with Deterministic Analyzer Layer

Extend the SDLC's existing `reviewer` sub-agent with a deterministic analyzer layer (Semgrep, Bandit, Radon, dependency-cruiser, gitleaks, jscpd, vulture, knip, Trivy, pydeps, cohesion, ESLint+sonarjs, Schemathesis, Pact), exposed as a Claude Code skill called `code-review`. A single `reviewer` sub-agent handles all projects; the operator picks a **review scope** (`lite`, `standard`, or `full`) at project setup time that controls which analyzers fire. No separate sub-agent files, no HTTP service, no separate process, no programmatic-pool billing.

The three scopes match three real project profiles:

- **`lite`** — quick PoCs and throwaway experiments. LLM-only review, no deterministic tools. Fast; minimal noise.
- **`standard`** — simple production projects. Security scanning (Semgrep, Bandit, gitleaks, Trivy) + code quality (Radon, vulture, jscpd, knip, ESLint+sonarjs) + LLM design review grounded by those findings. The default.
- **`full`** — complex brownfield projects. Everything in `standard` plus coupling/cohesion analysis (pydeps, dependency-cruiser, cohesion LCOM4) + contract testing (Schemathesis, Pact) at story boundaries. Accepts longer review time for deeper coverage.

The operator sets one config value (`review_scope`) in the SDLC skill's project-level config. They don't pick individual tools.

This replaces and simplifies the earlier `epic-reviewer-service` design (which extracted the same functionality into an HTTP service). The sub-agent shape keeps all the analyzer value while staying inside the operator's interactive Claude Code session.

## If/Then Hypothesis

**If we** extend the `reviewer` sub-agent with a deterministic analyzer layer whose depth is controlled by a single `review_scope` config (`lite` / `standard` / `full`), packaged as the `code-review` skill,

**for** the SDLC operator running the Review verb at per-task and story boundaries across projects that range from quick PoCs to complex brownfield codebases,

**then we will** give each project the right level of review rigor without per-tool configuration — `lite` stays fast for throwaway code, `standard` catches security and quality issues on production projects, and `full` adds coupling/cohesion and contract testing for complex multi-service codebases — while keeping the entire workflow inside the interactive Claude Code subscription pool.

## Why this is a hypothesis, not a commitment

Five assumptions could be wrong:

1. **That deterministic-layer + narrowed LLM design review beats LLM-only** at `standard` and `full` scope. Industry evidence (Sonar, OpenText, CASTLE benchmark) suggests yes. Worth measuring on this repo's actual diffs because the gain depends on rule-coverage match against this codebase's actual issues.
2. **That the sub-agent's turn budget can host both deterministic-result interpretation and design review** at `standard` and `full` scope without context exhaustion on large story-level diffs. The LLM call sits inside one turn alongside spec-reading and fix-task spawning. If story-level diffs grow beyond a turn's context budget, the design-review step may need to be a separate sub-agent dispatch.
3. **That SARIF (extended with `properties.sdlc_severity`) is the right canonical format** for the deterministic layer to hand to the sub-agent. The format fits findings well; if the SDLC workflow ends up needing decision-shaped output for the design step, the format may need supplementing.
4. **That every analyzer can run cleanly inside the operator's `/sandbox`-enabled Claude Code session** with only narrow, documented widening of `allowedDomains` (for contract-test targets at `full` scope) and no widening of `allowWrite`, `excludedCommands`, or `allowUnsandboxedCommands`. If any analyzer turns out to need broader privilege, we either find an alternative tool or accept a documented operator-side widening with an ADR.
5. **That three scopes (`lite` / `standard` / `full`) are the right granularity.** If operators find themselves frequently wanting "standard + dependency-cruiser but not cohesion," the coarse model breaks and we'd need a finer-grained selection. The bet is that the three natural project profiles (PoC, simple production, complex brownfield) absorb the meaningful variation and individual-tool selection would add configuration burden without proportional value.

s0 and s1 prove assumption 3 (the deterministic SARIF layer is usable). s1's `setup.sh` and `--capabilities` runtime check prove assumption 4 for the offline-prefetch path. s5 proves assumptions 1, 2, 4, and 5 end-to-end (all three scopes work against real diffs in a real sandboxed session). Assumption 5 is validated by operator experience across the three project profiles during the validation window.

## What's intentionally not in scope

These are deliberate non-goals, recorded here so they don't drift back in mid-epic:

- **No per-tool selection for the operator.** The operator picks a scope; the skill maps scopes to tool sets. If a future operator genuinely needs to add one tool to `standard` that's normally only in `full`, the config allows overrides via `code-review.toml`'s `[scope_overrides]` section — but the three scopes are the primary interface and the overrides are not promoted in the SKILL.md's quick-start section.
- **No HTTP service.** Earlier design (`epic-reviewer-service`) extracted analysis into a daemon. We're not doing that. Reasons: interactive-subscription billing model, simpler operational footprint, single-operator scale doesn't justify a service.
- **No async job queue, no workspace isolation, no result cache.** The sub-agent's turn is the unit of work; subprocesses run synchronously within it.
- **No unattended/CI invocation in this epic.** A future epic could add a thin CI wrapper that calls the same analyzer CLI, but that path uses the Agent SDK credit pool, not the interactive subscription. Not now.
- **No service-style capability discovery endpoints.** Capability declaration becomes static metadata in `capabilities.json` referenced from `SKILL.md` — useful for self-description and audit, not a runtime API.
- **No multi-tenant or multi-repo support.** Single operator, single repo per session.
- **No reliance on unsandboxed execution.** The skill must work under the operator's strict-sandbox configuration; analyzers that would require widening the sandbox beyond the documented `allowedDomains` for contract-test targets (at `full` scope) are out of scope and a future operator-approved ADR.
- **No SDLC-version check at runtime.** The architecture depends on the SDLC contract surface enumerated in the architecture's §17, treated as stable by convention. There is no parser, no compatibility range, no refusal-to-load on unknown SDLC versions.

## Tiny Acts of Discovery Experiments

**We will test our assumption by:**

- Building the s0 analyzer façade with Semgrep + Radon adapters, and exercising it via the CLI (`python -m code_review.cli --review-scope standard --scope per-task --diff <ref>`) against a fixture diff with known issues. Confirms the SARIF shape is usable before any sub-agent integration.
- Wiring the skill's `capabilities.json` and the `reviewer` sub-agent to read the `review_scope` config and select the correct analyzer set (s1 + s5). Confirms the scope-to-tool mapping works without the operator touching individual tools.
- Running the consolidated analyzer set at `standard` scope against 10 recent task diffs from this repo and recording per-axis findings. Compare against `lite` scope (LLM-only, same as the current reviewer's output) on the same diffs.
- Manually running a per-task review at `standard` scope on a fixture diff containing a planted design issue (e.g., function named `process_data` that handles authentication) that no deterministic rule will catch. Confirms the LLM design step still surfaces issues that rules can't, with the deterministic context successfully suppressing duplicate findings.
- Running one full per-task close end-to-end at `standard` scope (deterministic + LLM design + fix-task spawning per rule #25) on a real task in this repo. Confirms the SDLC auto-remediation loop still closes correctly.
- Running one story-level review at `full` scope on a fixture with planned inter-service spec drift. Confirms Schemathesis / Pact contract testing fires at story boundaries but not at per-task timing.

## Validation Measures

**We know our hypothesis is valid if within 3 weeks** of s0–s5 shipping **we observe:**

- **Finding overlap (`standard` scope):** ≥ 70% of `lite`-scope findings on the 10-diff comparison sample are also produced by the deterministic layer, confirming that the rule-based tools cover what the LLM was previously redoing (quantitative).
- **Precision on design findings:** for findings the LLM design step surfaces that the deterministic layer does *not* (at `standard` scope), operator agreement is ≥ 70% (quantitative). The LLM's narrowed scope should improve hit rate vs. `lite`-scope baseline.
- **Context budget headroom:** on the largest story-level diff the loop encounters during the validation window (at `full` scope), the sub-agent's turn completes the deterministic-result interpretation + design review + fix-task spawning without running into context-window pressure (qualitative; observable from turn metadata).
- **Workflow stability:** the SDLC's rule #25 2-round remediation bound, the `-fix<N>-` naming convention, and the per-task vs. story-level distinction all work unchanged at every scope (qualitative — no `/sdlc/SDLC.md` text changes required to integrate).
- **Subscription pool only:** zero Agent SDK credit consumption attributed to Reviewer work during the validation window at any scope (quantitative). All LLM calls happen inside the operator's interactive Claude Code session.
- **Sandbox-clean operation:** every per-task review at every scope during the validation window completes in a `/sandbox`-enabled session with strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`) without prompting the operator for additional widening and without any `dangerouslyDisableSandbox` retry (quantitative — instrumented in CI's sandbox-compatibility test).
- **`lite` scope fidelity:** `lite` scope produces output functionally equivalent to the current SDLC reviewer's output — same review quality, same speed, no unexpected deterministic findings (qualitative — confirms that `lite` is a genuine no-change path for PoC projects).
- **Scope switch is instant:** an operator can change `review_scope` from `lite` to `standard` to `full` (and back) by editing the SDLC skill's config, with no other action, and observe the corresponding analyzer set on the next Review dispatch (qualitative).

**We know the hypothesis is invalidated if:**

- Finding overlap is < 30% (the deterministic layer isn't catching what the LLM was catching, so layering doesn't help).
- The sub-agent's turn runs out of context on routine story-level diffs at `standard` scope (assumption 2 fails — design review needs its own dispatch even for the common case).
- The SDLC's workflow text requires changes to accommodate the scope-based output (assumption 5 fails — the abstraction is wrong).
- Any analyzer turns out to require sandbox widening beyond the contract-test `allowedDomains` entries documented in `SKILL.md` (assumption 4 fails — we need either a different tool or an operator-approved ADR).
- Operators consistently override the scope-to-tool mapping for individual projects (assumption 5 fails — three scopes aren't the right granularity and we need finer control).

## Stories

Sequenced for build order. Each story is independently mergeable. Epic does not close until s0–s5 are all done; there's no minimum-viable subset because the value only lands once the sub-agent actually uses the analyzers.

0. **s0-analyzer-facade-and-two-adapters** — Define the `Analyzer` Protocol and canonical SARIF / MetricSet types. Ship Semgrep and Radon adapters as reference implementations. Ship a CLI (`python -m code_review.cli`) that runs configured analyzers against a diff and emits consolidated JSON. CLI accepts `--review-scope` to select the analyzer set. No sub-agent integration yet. *Prerequisite for everything else.*

1. **s1-reviewer-skill-and-capabilities** — Package the analyzer code as a Claude Code skill at `.claude/skills/code-review/`. Includes `SKILL.md`, `capabilities.json` (review kinds, stack coverage, taxonomies, analyzer registry, scope-to-analyzer mapping), JSON Schemas for request/response shapes, the CLI entry point the sub-agent will invoke, and a `setup.sh` that handles offline cache pre-fetch. Skill is loadable but not yet wired into the `reviewer` sub-agent.

2. **s2-aggregator-and-severity-mapping** — SARIF deduplication by `(file, line, ruleId-family / CWE)`. Severity mapping from SARIF `level` + `properties.severity` into the SDLC's Critical / Important / Minor / Nit taxonomy (lines 166–169 of SDLC.md). Ranked-hotspots output for the sub-agent's auto-remediation step.

3. **s3-remaining-deterministic-adapters** — Bandit, gitleaks, Trivy, jscpd, vulture, knip, dependency-cruiser, ESLint+sonarjs, pydeps, cohesion. SARIF normalisation shims for tools whose native output isn't SARIF. Each new adapter appears in the skill's `capabilities.json` analyzer registry and is assigned to one or more review scopes.

4. **s4-contract-testing-adapters** — Schemathesis (schema-driven, runs against a live API) and Pact (consumer-driven, broker-published). Story-level scope only, longer timeout budgets. Assigned to `full` review scope. Scope restrictions declared in `capabilities.json`.

5. **s5-subagent-integration-and-design-review** — Update `.claude/agents/reviewer.md` to read the SDLC skill's `review_scope` config, invoke the `code-review` skill's CLI with the appropriate scope, then perform LLM design review as part of its own turn using the deterministic SARIF as grounding context. At `lite` scope, the sub-agent skips the CLI and does LLM-only review (matching the current behaviour). Includes the prompt structure for design review, the "do not duplicate deterministic findings" instruction, and the fix-task spawning per rule #25. This is where the hypothesis is actually tested end-to-end.

## Convert-to-stories note

Stories sit alongside this epic in `/sdlc/work/active/` and follow the `s<N>-<slug>` naming convention per SDLC file conventions (line 80). Tasks under each story carry `s<N>-t<M>-<slug>` ids and are not pre-drafted — task decomposition happens at Plan time per the SDLC's Plan verb.

## Relationship to the older epic-reviewer-service draft

A prior version of this work was framed as an HTTP service (`epic-reviewer-service` with eight stories s0–s8, including FastAPI, async job queue, capability endpoints, observability spans). That design was rejected in favour of this sub-agent approach for three reasons:

1. The Agent SDK billing change (effective June 15, 2026) makes programmatic Claude Code use draw from a separate credit pool at API rates, undermining the "use the subscription" goal.
2. The single-operator interactive workflow doesn't justify the operational complexity of a service.
3. The SDLC's existing sub-agent pattern is the natural home for review logic.

The older epic file is preserved for context; the deterministic-analyzer engineering work (s0, s2–s4 here) is substantially the same — only the transport changed from HTTP to direct CLI invocation by the sub-agent.

---

---
id: s0-analyzer-facade-and-two-adapters
kind: story
project: sdlc
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

---

---
id: s1-reviewer-skill-and-capabilities
kind: story
project: sdlc
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26  # scope model: single reviewer, lite/standard/full scopes
---

# s1 — Reviewer skill packaging and capability declaration

## Summary

Package the s0 analyzer code as a Claude Code skill at `.claude/skills/code-review/` so the sub-agent (s5) can discover and invoke it through the standard skill convention. Includes a `SKILL.md` describing the skill, a static `capabilities.json` declaring what the skill can do (review kinds, stack coverage, taxonomies, analyzer registry), JSON Schemas for the request/response shapes the sub-agent exchanges with the CLI, the `pyproject.toml` + `package.json` + lockfiles that pin every dependency, and `scripts/setup.sh` which installs everything and pre-fetches the offline data later stories' adapters need (Trivy DB, Semgrep rule packs).

No service endpoints — capability declaration is static metadata, not a runtime API. The discipline pays off in three places: the sub-agent can grep the skill to know what analyzers exist without hardcoding, the operator can audit coverage by reading one file, and adding an analyzer in s3/s4 means a single capabilities-registry entry rather than scattered edits.

The setup script is the seam between a fresh checkout and a runnable skill. Because Claude Code's sandbox blocks network at runtime by default, `setup.sh` is the one place where network fetches happen — once, deliberately, before the skill is ever used inside the sandbox. After it has run, the skill is fully self-contained.

## Use Case

- **As a** Reviewer sub-agent (or the operator inspecting what review coverage looks like)
- **I want to** read a single declarative file that lists every review kind, every supported stack, every analyzer and its status, and the taxonomies findings are tagged against
- **so that** I can plan a review without hardcoding analyzer lists in agent prompts, detect at runtime if a required binary is missing, and self-document the service for operator audit

## Acceptance Criteria

### Scenario: Skill is discoverable via the standard Claude Code skill convention

- **Given** the skill is installed at `.claude/skills/code-review/SKILL.md`
- **When** a Claude Code session starts and the operator references the skill (or the reviewer sub-agent loads)
- **Then** the skill appears in the available skills list with the description from `SKILL.md`'s frontmatter, and the SKILL.md content explains the CLI invocation pattern, the request/response shapes, and links to `capabilities.json` and the JSON Schemas

### Scenario: capabilities.json declares review kinds

- **Given** `.claude/skills/code-review/capabilities.json` exists
- **When** I parse it
- **Then** the document contains a `review_kinds` array including at minimum `per-task`, `story-level`, and `contract-verification`, each with `id`, `description`, `scope` (one of: `diff`, `cumulative-diff`, `story-level-only`), and `expected_duration_s` range; the JSON validates against `schemas/capabilities.json`

### Scenario: capabilities.json declares stack coverage

- **Given** the capabilities document
- **When** I read its `stack_coverage` section
- **Then** it lists Python (with `version_range`, supported frameworks including `fastapi` and `django` with their version ranges, and an `analyzer_classes` list) and TypeScript (with frameworks `next`, `react`, `vite` and their version ranges); values reflect what's been verified by the test suite, not aspirational compatibility

### Scenario: capabilities.json declares the analyzer registry

- **Given** the capabilities document
- **When** I read the `analyzers` section
- **Then** it contains one entry per registered analyzer (s0 adds `semgrep` and `radon`; s3 and s4 add the rest), each with `id`, `kind` (`deterministic` | `llm` | `deterministic-runtime`), `languages`, `rule_classes` (e.g. `security`, `complexity`, `secrets`), `taxonomies_tagged` (e.g. `cwe`, `owasp-top-10`), `default_timeout_s`, and any `scope_restriction`

### Scenario: capabilities.json declares taxonomies

- **Given** the capabilities document
- **When** I read its `taxonomies` section
- **Then** it lists CWE (with version), OWASP Top 10 (with version), and the SDLC severity taxonomy (with the four values `critical`, `important`, `minor`, `nit`); findings emitted by the aggregator (s2) will reference these via SARIF's `taxa` mechanism, not free-form tags

### Scenario: JSON Schemas are addressable from the SKILL.md

- **Given** `SKILL.md` links to `schemas/review-request.json` and `schemas/review-response.json`
- **When** I fetch each
- **Then** each is a valid JSON Schema (draft 2020-12 or later) describing the CLI's expected input arguments and the consolidated JSON output shape from s0, suitable for runtime validation by the sub-agent or any external consumer

### Scenario: CLI advertises a --capabilities flag for runtime introspection

- **Given** the CLI from s0 is installed
- **When** I run `python -m code_review.cli --capabilities`
- **Then** the CLI prints to stdout a JSON document combining the static `capabilities.json` with runtime checks for each analyzer (e.g. `semgrep.status == "available"` if the binary resolves on PATH, `"unavailable"` with an `error` field otherwise); the static section matches the file content; the runtime section is recomputed each invocation

### Scenario: A missing required binary is visible before a review runs

- **Given** the operator wants to run a review that requires gitleaks (added in s3) but gitleaks is not on PATH
- **When** the sub-agent (s5) or an operator runs `python -m code_review.cli --capabilities`
- **Then** `analyzers.gitleaks.status == "unavailable"` with a clear error message; this lets the sub-agent escalate via the Autonomy gate before submitting a review that would silently miss secrets scanning

### Scenario: Adding a new analyzer is a single registry edit

- **Given** I add a new adapter class implementing the `Analyzer` Protocol (s3 / s4)
- **When** I add one entry to `capabilities.json`'s `analyzers` array describing it
- **Then** the analyzer appears in `--capabilities` output without any other code changes; the CLI accepts it as a `--analyzer <name>` argument; the skill's documentation does not need to be updated

### Scenario: setup.sh installs everything in one command

- **Given** a fresh checkout of the skill with no `node_modules/` and no `cache/`
- **When** I run `./scripts/setup.sh` from the skill directory (outside the sandbox, since the script needs network access)
- **Then** the script runs `uv sync --frozen` (Python deps), `npm ci` (Node deps for JS analyzers), `python scripts/prefetch_caches.py` (downloads the Trivy DB and Semgrep rule packs into `cache/`), and copies the sub-agent file from the skill repo to the host project at `.claude/agents/reviewer.md`; the script is idempotent — re-running it when caches exist refreshes them but doesn't fail; the script exits non-zero with a clear error if any step fails

### Scenario: Installing the skill updates the existing reviewer sub-agent

- **Given** a host project that has the SDLC skill installed with its existing `.claude/agents/reviewer.md`
- **When** the operator runs `./scripts/setup.sh` to install the `code-review` skill
- **Then** the setup script updates `.claude/agents/reviewer.md` to include scope-aware behaviour (reading `review_scope` from the SDLC config). At `lite` scope the reviewer behaves identically to before installation; the `code-review` skill's CLI is only invoked at `standard` or `full` scope.

### Scenario: The operator selects the review scope via SDLC config

- **Given** the `code-review` skill is installed
- **When** the operator sets `review_scope = "standard"` (or `"full"`) in the SDLC skill's project-level config
- **Then** the next SDLC Review dispatch runs the deterministic analyzer layer at the configured scope before the LLM design review step; changing the config to a different scope (or back to `"lite"`) takes effect on the next dispatch; no other operator action is required

### Scenario: Skill works inside the sandbox after setup.sh has run

- **Given** `./scripts/setup.sh` has completed successfully
- **and Given** the operator's Claude Code session has `/sandbox` enabled in auto-allow mode
- **When** the sub-agent (s5) invokes the CLI
- **Then** every analyzer subprocess starts and runs to completion inside the sandbox without prompting the operator for filesystem or network widening; no `excludedCommands` entries are needed; no `allowUnsandboxedCommands` retries occur. This is the single integration property that makes the architecture's sandbox-compatibility claim concrete.

### Scenario: SKILL.md documents scopes, install, and sandbox configuration

- **Given** the operator has just downloaded the `code-review` skill and wants to use it
- **When** they read `SKILL.md`
- **Then** SKILL.md includes, in order: (1) a "Review scopes" section explaining what `lite`, `standard`, and `full` each do, with a one-sentence description per scope and guidance on which project profile each suits (PoC, simple production, complex brownfield), (2) an "Install" section explaining `./scripts/setup.sh`, (3) a "Configure" section showing the one-line `review_scope = "standard"` config change (with examples of all three values), (4) a "Sandbox configuration" section with a copy-paste `.claude/settings.json` snippet showing the recommended strict defaults and explaining how to add Schemathesis/Pact target hosts to `allowedDomains` at `full` scope

## Test specification

- **SKILL.md presence and structure test** — assert the file exists at the expected path, has frontmatter with required fields per the Claude Code skill convention, and references the schema files.
- **capabilities.json schema-validation test** — fetch both `capabilities.json` and `schemas/capabilities.json`, validate using `jsonschema`; assert all required sections (`review_kinds`, `stack_coverage`, `analyzers`, `taxonomies`) are present.
- **Runtime introspection test** — invoke `python -m code_review.cli --capabilities` against a controlled environment (one analyzer's binary on PATH, another removed); assert the output reflects the actual environment state.
- **Schema referenceability test** — assert `schemas/review-request.json` and `schemas/review-response.json` are valid JSON Schema and that fixture request/response examples from s0 validate against them.
- **Analyzer-registry round-trip test** — add a synthetic adapter and an entry in `capabilities.json`; assert it appears in `--capabilities` output and the CLI accepts it without code change.
- **Coverage discipline test** — assert each `stack_coverage` framework entry has at least one corresponding test fixture under `tests/fixtures/`, enforcing the "verified, not aspirational" discipline.
- **setup.sh idempotency test** — run the script, capture state, run it again, assert no breakage and that already-cached artefacts aren't redundantly re-downloaded (script uses content-addressed checks).
- **Scope-dispatch test** — install the skill, set `review_scope` to each of `lite`, `standard`, `full` in turn; at `lite`, assert no CLI subprocess was spawned; at `standard`, assert the CLI received `--review-scope standard`; at `full`, assert `--review-scope full`.
- **Install-idempotency test** — run `setup.sh` twice; assert the second run produces no errors and the resulting `.claude/agents/reviewer.md` is identical to the first run's output.
- **Sandbox-installable test** — run `setup.sh` outside sandbox, then invoke the CLI's `--capabilities` inside a fresh `/sandbox`-enabled session; assert every analyzer reports `available` (assuming all underlying binaries are present); assert no permission prompts fire and no `dangerouslyDisableSandbox` retries occur.
- **SKILL.md sandbox-snippet test** — parse the JSON code block in SKILL.md's "Sandbox configuration" section; assert it's valid `settings.json` syntax with the expected strict defaults.
- **SKILL.md scope-doc test** — assert SKILL.md contains sections for "Review scopes", "Install", "Configure", and "Sandbox configuration" by header presence; assert the "Review scopes" section names all three values (`lite`, `standard`, `full`).

## Out of scope (deferred to later stories)

- Aggregation, deduplication, severity mapping (s2).
- Adapters beyond s0's Semgrep + Radon (s3, s4).
- Actual sub-agent invocation of the skill (s5).
- Dynamic capability changes mid-session — capabilities are static for a process lifetime.
- Cross-skill federation or capability inheritance — single skill in this story.

---

---
id: s2-aggregator-and-severity-mapping
kind: story
project: sdlc
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26
---

# s2 — Aggregator with dedup and SDLC severity mapping

## Summary

Consolidate per-analyzer SARIF outputs into a single review-level SARIF report, deduplicating findings that multiple analyzers report on the same location. Map SARIF `level` + `properties.severity` into the SDLC's Critical / Important / Minor / Nit taxonomy (lines 166–169 of SDLC.md). Produce a ranked-hotspots list (per-file composite score) for the sub-agent's auto-remediation step (rule #25).

The aggregator runs inside the CLI from s0 — given multiple `--analyzer` arguments, the CLI fans out, then the aggregator consolidates before emitting the final consolidated document.

## Use Case

- **As a** Reviewer sub-agent (s5) processing the CLI's output
- **I want to** receive a deduplicated SARIF report with each finding tagged in the SDLC's severity taxonomy, plus a per-file ranked hotspot list
- **so that** I can apply rule #25's auto-remediation rules (file Critical/Important as fix tasks, append Minor to notes, drop Nit) without writing per-analyzer parsing logic, and so that I can pick the top-N files to refactor first

## Acceptance Criteria

### Scenario: Two analyzers flagging the same line produce one consolidated finding with multiple sources

- **Given** Semgrep and Bandit both produce findings at `src/auth.py:47` for related vulnerability classes (both tag CWE-89)
- **When** the aggregator runs
- **Then** the consolidated SARIF contains exactly one `result` at that location, with `properties.sources` listing both `semgrep` and `bandit`, and the highest severity from either source preserved in the merged result

### Scenario: Findings within a 3-line tolerance on the same file and same CWE are merged

- **Given** Semgrep reports a finding at `src/auth.py:47` and Bandit reports the equivalent at `src/auth.py:49`, both tagged CWE-89
- **When** the aggregator runs
- **Then** they merge into a single finding (lower line number wins), with `properties.original_locations` listing both line numbers for audit

### Scenario: Findings without a shared CWE do not merge even at the same line

- **Given** two findings at `src/auth.py:47` with different CWE values
- **When** the aggregator runs
- **Then** both findings appear in the consolidated output as separate `result` entries; CWE is the merge anchor, not file+line alone

### Scenario: Severity mapping applies the SDLC taxonomy

- **Given** consolidated findings with mixed `level` and `properties.severity` values
- **When** the severity mapper runs
- **Then** each finding gains a `properties.sdlc_severity` field with one of `critical`, `important`, `minor`, `nit`, mapped as: `level==error` ∨ `properties.severity in {critical}` → `critical`; `level==warning` ∧ `properties.severity in {important, high}` → `important`; `level==warning` (no severity) → `minor`; `level==note` ∨ `properties.severity in {nit, info}` → `nit`. The mapping table lives in `code_review/severity.py`, not inline in adapter code.

### Scenario: Ranked hotspots reflect a multi-axis composite score

- **Given** consolidated findings across several files plus the merged MetricSet from complexity/coupling/cohesion analyzers
- **When** the aggregator computes hotspots
- **Then** each touched file gets a `composite_score` and a list of contributing factors (severity-weighted finding count, cyclomatic complexity, fan-in+fan-out, inverse cohesion if available); the output is a `ranked_hotspots` list of `{file, composite_score, factors}` sorted descending. Weights live in `capabilities.json` or a sibling `code-review.toml`, not in code.

### Scenario: Per-task and story-level scopes produce different hotspot scopes

- **Given** a CLI invocation with `--scope per-task` and another with `--scope story-level` against the same diff
- **When** both complete
- **Then** the per-task hotspots are restricted to files in the diff; the story-level hotspots include cross-task patterns (e.g., a fan-out finding that only emerges when looking at all files together) and may include files not directly modified

### Scenario: CWE taxonomy is referenced via SARIF taxa, not free-form tags

- **Given** a finding tagged with a CWE identifier
- **When** I inspect the consolidated SARIF
- **Then** the CWE reference appears in the result's `taxa` array (per SARIF 2.1.0's taxonomy mechanism), the run declares the CWE taxonomy in `tool.driver.supportedTaxonomies`, and the same finding does not duplicate the CWE id as a free-form `tag`

### Scenario: Operator can override aggregation thresholds without code changes

- **Given** `.claude/skills/code-review/code-review.toml` sets `dedup.line_tolerance = 5` and overrides one severity mapping entry
- **When** the aggregator loads config and runs
- **Then** the line tolerance and severity mapping reflect the config; defaults apply for unset values

### Scenario: Consolidated output validates against the response schema from s1

- **Given** a completed aggregation run
- **When** the consolidated JSON is validated against `.claude/skills/code-review/schemas/review-response.json`
- **Then** validation succeeds; all required fields are present; SARIF substructure validates against the SARIF 2.1.0 schema

## Test specification

- **Dedup correctness test** — fixture SARIF inputs from 3 mock analyzers with planned overlaps, assert exact dedup outcomes (same-line, near-line, different-CWE).
- **Severity mapping table test** — exhaustive table-driven test covering each input combination → expected SDLC severity.
- **Composite score test** — golden-file test: given known SARIF + MetricSet inputs, assert ranked-hotspots output matches expected JSON.
- **Scope-difference test** — same diff, two runs with different `--scope`, assert hotspots reflect the scope (per-task restricted to changed files; story-level may include unchanged files).
- **Config override test** — load a `code-review.toml` with overrides, assert behaviour reflects the overrides.
- **CWE taxonomy reference test** — fixture with a known CWE-tagged finding, assert the SARIF result references CWE via `taxa`, the run declares `supportedTaxonomies`, and no duplicate `tags` entry exists.
- **Response-schema validation test** — round-trip a consolidated output through the s1 response schema; assert no required fields are dropped during dedup.

## Out of scope (deferred to later stories)

- Sub-agent's actual fix-task spawning logic (s5) — this story produces the input the sub-agent will consume.
- Cross-review historical trending (e.g., "Critical findings over the last 10 commits") — out of scope for this epic; filesystem-walking trend scripts are a future addition.
- Architectural-drift detection across stories — story-level scope produces useful per-review output but doesn't yet do cross-story trend analysis.
- Custom severity mapping per-project beyond the skill's `code-review.toml` — single skill-level config.

---

---
id: s3-remaining-deterministic-adapters
kind: story
project: sdlc
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

---

---
id: s4-contract-testing-adapters
kind: story
project: sdlc
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26  # sandbox compatibility: allowedDomains, cache redirection
---

# s4 — Contract testing adapters (Schemathesis, Pact)

## Summary

Add Schemathesis (schema-driven; runs against a live API) and Pact (consumer-driven; reads contracts from a broker) as analyzers. These differ structurally from s3 adapters — they're slower, they may require a running service or broker, and they're only meaningful at story-level scope, not per-task. Normalise their output (JUnit XML, Pact's own JSON) into SARIF so they slot into the same aggregator (s2). Scope restrictions and longer default timeouts are declared in `capabilities.json` (s1).

## Use Case

- **As a** SDLC operator with a FastAPI backend and a Next.js frontend that consumes its API
- **I want to** include contract-testing findings in story-level reviews
- **so that** I catch backend changes that drift from the OpenAPI spec (Schemathesis) and backend changes that break the frontend's actual consumption pattern (Pact), without writing separate CI plumbing for each tool

## Acceptance Criteria

### Scenario: Schemathesis adapter runs against a live API and produces SARIF

- **Given** a fixture FastAPI service running on `localhost:8080` with an OpenAPI spec at `/openapi.json` that contains a deliberate drift (e.g., an endpoint returns `username` but the spec says `user_name`)
- **When** the Schemathesis adapter runs with `spec_url=http://localhost:8080/openapi.json`
- **Then** the output SARIF contains at least one `result` whose `ruleId` is `schemathesis.response_schema_violation`, whose `message.text` names the divergent field, and whose `properties.endpoint` records the failing endpoint

### Scenario: Pact adapter verifies provider against broker-published contracts

- **Given** a fixture Pact broker (Docker container) holding one consumer contract for a known endpoint
- **and Given** a fixture provider service that satisfies the contract
- **When** the Pact adapter runs with `broker_url=...` and `provider=fixture-api`
- **Then** the output SARIF reports verification success with no findings; modifying the provider to break the contract produces a `result` with `ruleId: pact.contract_violation` and `properties.consumer` naming which consumer's contract broke

### Scenario: Contract adapters are only available at story-level scope

- **Given** the CLI is invoked with `--scope per-task --analyzer schemathesis`
- **When** the CLI validates the invocation
- **Then** the CLI exits with a clear error stating that contract adapters require `--scope story-level`; the same invocation with `--scope story-level` is accepted

### Scenario: Contract adapters honour longer timeout budgets

- **Given** the Schemathesis adapter is configured with a default timeout of 600 seconds (vs. 60–180 for s3 adapters), declared in `capabilities.json`
- **When** I check the timeout configuration
- **Then** contract adapters' timeouts are at least 5x the deterministic-adapter defaults, configurable via `code-review.toml`, and time-budgeted exhaustion produces a clean `status: "timeout"` outcome with the adapter's partial findings (if any) preserved

### Scenario: Adapter fails cleanly when its prerequisite isn't reachable

- **Given** the Pact broker URL is unreachable, or the Schemathesis target API isn't running
- **When** the adapter runs
- **Then** the adapter returns `AnalyzerOutput` with `error` populated naming the reachability issue, the CLI's consolidated output reflects the failure per-analyzer, and the deterministic-layer SARIF from other analyzers is preserved

### Scenario: Contract findings carry severity mapped to Critical

- **Given** a contract violation finding from either Schemathesis or Pact
- **When** it flows through the s2 severity mapper
- **Then** `properties.sdlc_severity == "critical"` by default (contract violations break inter-service correctness — line 166 of SDLC.md), unless overridden in `code-review.toml`

### Scenario: Auth is configurable per-target

- **Given** the Schemathesis target requires Bearer auth
- **When** the adapter is invoked with `auth: {type: bearer, token_env: "FIXTURE_API_TOKEN"}` in its config
- **Then** the adapter reads the token from the named env var (not from request payload or CLI args) and sends it on every request; the token never appears in logs, the consolidated output, or any artefact the sub-agent reads

### Scenario: Contract adapters are the only analyzers that need runtime network access

- **Given** the operator's Claude Code session has `/sandbox` enabled with no `allowedDomains` widening (i.e. only per-task review works)
- **When** the operator attempts a story-level review that would include contract testing
- **Then** the Schemathesis and Pact adapters fail with `status: "error"` and an `error` field naming the specific host (e.g. "Schemathesis target `http://localhost:8080` not reachable; check that the host is in `sandbox.allowedDomains`"); the consolidated output exits non-zero; other adapters' results are preserved; the sub-agent escalates to the operator with a clear remediation path
- **and Given** the operator subsequently adds the target host to `sandbox.allowedDomains` and retries
- **Then** the contract adapters complete successfully

### Scenario: Contract adapters' cache writes stay inside CWD

- **Given** the Schemathesis adapter is running (which uses Hypothesis-based fuzzing with a `.hypothesis/` cache)
- **When** I monitor filesystem writes during a Schemathesis run
- **Then** every write target is inside the project's CWD — Schemathesis's `.hypothesis/` is redirected to `.claude/skills/code-review/cache/hypothesis/` via the `HYPOTHESIS_STORAGE_DIRECTORY` environment variable; the same applies to any Pact verification log files (configured to `.claude/skills/code-review/cache/pact/`)

### Scenario: SKILL.md documents which domains the operator must allowlist

- **Given** an operator setting up the skill for story-level reviews
- **When** they read `SKILL.md`'s "Sandbox configuration" section (added in s1)
- **Then** they find an explicit subsection on contract testing that says: "Story-level reviews invoke Schemathesis and Pact. Both need network access to the targets you configure in `code-review.toml`'s `[contract_testing]` section. Add only those specific hosts (e.g., `localhost`, your internal broker hostname) to `sandbox.allowedDomains` — never widen to wildcards or public-internet hosts."

## Test specification

- **Schemathesis adapter integration test** — fixture FastAPI service with a planned spec drift; assert the drift surfaces with the expected `ruleId`.
- **Pact adapter integration test** — Dockerized Pact broker fixture + fixture provider; happy path + broken-provider path; assert SARIF outputs match expectations.
- **Scope-validation test** — `per-task` + contract analyzer → CLI error; `story-level` + contract analyzer → accepted.
- **Timeout-budget test** — config-driven timeout values applied; exhaustion produces `status: "timeout"` with partial findings preserved.
- **Reachability-failure test** — broker URL is `http://localhost:1` (unreachable); adapter fails cleanly with informative error; other analyzers' results preserved.
- **Sandbox-blocked-network test** — run contract adapters with the network stack patched to simulate sandbox denial of the configured target; assert the error message explicitly names `sandbox.allowedDomains` as the likely cause.
- **Hypothesis cache-redirect test** — set `HOME` to an empty temp dir, run Schemathesis; assert all `.hypothesis/` writes land under `.claude/skills/code-review/cache/hypothesis/` and none under the temp `HOME`.
- **Severity-mapping test** — contract violations route to `critical` after s2 mapping.
- **Auth secrecy test** — assert the token never appears in the consolidated output, in `analyzers.<name>.raw_output` (if present for debugging), or in CLI argument logs.

## Out of scope (deferred to later stories)

- GraphQL contract testing — Schemathesis supports it but the fixture / test surface is separate work.
- gRPC / Protobuf contract testing — out of this epic.
- AsyncAPI (event-driven systems) — separate epic if needed.
- Running Schemathesis in stateful "links" mode for multi-step API flows — single-operation mode is the default in this story.
- Operating the Pact broker as part of the skill's deployment — the broker is an external dependency the operator runs separately.
- Bi-directional contract testing (Pactflow's exclusive) — basic consumer-driven contracts only.

---

---
id: s5-subagent-integration-and-design-review
kind: story
project: sdlc
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26  # scope model: single reviewer sub-agent with lite/standard/full review scopes
---

# s5 — Sub-agent integration with LLM design review inside the turn

## Summary

Update `.claude/agents/reviewer.md` to read the SDLC skill's `review_scope` config (`lite` / `standard` / `full`) and branch accordingly. At `lite` scope, the sub-agent does LLM-only review (matching the current behaviour). At `standard` and `full` scope, it invokes the `code-review` skill's CLI for deterministic analysis, then performs LLM design review *as part of its own turn* using the deterministic SARIF as grounding context. This is the keystone story — every previous story builds toward this one, and the hypothesis is tested here.

The sub-agent's flow at `standard` / `full` scope:

1. Read the spec, plan, and diff.
2. Read `review_scope` from the SDLC skill's project-level config.
3. Invoke the `code-review` skill's CLI via the Bash tool: `python -m code_review.cli --review-scope <scope> --scope <timing> --diff <range> --output .claude/skills/code-review/runs/<id>.json`. The output path is project-relative so the file lands inside the sandbox's default writable region.
4. Read `.claude/skills/code-review/runs/<id>.json` — the consolidated, deduplicated, severity-mapped SARIF + metrics + ranked hotspots from s0–s4.
5. **In the same turn**, perform LLM design review: read the diff, read the deterministic findings, and surface only the design / naming-intent / architectural issues the rule-based layer can't catch.
6. Merge design findings into the SARIF (`ruleId` prefixed `llm-design.*`, `properties.severity` per the SDLC taxonomy).
7. File `-fix<N>-` tasks for Critical/Important per rule #25, append Minor to the parent task's `notes:`, drop Nit.

At `lite` scope, steps 2–4 are skipped — the sub-agent goes directly to step 5 without deterministic context.

Step 5 is the only LLM step at any scope. It happens inside the sub-agent's turn, drawing from the interactive Claude Code subscription pool by construction. No HTTP service, no Agent SDK credit, no separate process. The flow runs cleanly under the operator's `/sandbox`-enabled session without requiring any unsandboxed retries.

## Use Case

- **As a** SDLC operator running the Review verb at task close or story boundary
- **I want to** set a `review_scope` once per project (`lite` for PoCs, `standard` for production, `full` for complex brownfield) and have the single `reviewer` sub-agent adjust its behaviour accordingly — without configuring individual tools
- **so that** quick projects stay fast, production projects get security and quality coverage, complex projects get full coupling and contract testing, and the entire workflow stays on the interactive subscription pool

## Acceptance Criteria

### Scenario: Sub-agent invokes the skill CLI at per-task review time

- **Given** a task has just passed Verify (per the SDLC's Verify verb)
- **When** the SDLC loop dispatches the Review sub-agent
- **Then** the sub-agent invokes `python -m code_review.cli --scope per-task --diff <base>..<head> --output <path>` via the Bash tool with the task's commit range, then reads the output file; no analysis logic is inlined in the sub-agent's prompt — the analyzer set is determined by the skill's `capabilities.json` and any explicit `--analyzer` overrides

### Scenario: Sub-agent reads the skill's capabilities before invoking

- **Given** the sub-agent is preparing to invoke a review
- **When** it constructs the CLI invocation
- **Then** it first runs `python -m code_review.cli --capabilities` to discover which analyzers are available, verifies that any policy-required analyzers (e.g. gitleaks for the SDLC's secrets gate) have `status: available`, and escalates via the Autonomy gate if a required analyzer is unavailable rather than submitting an invocation that would silently lack coverage

### Scenario: LLM design review is performed inside the sub-agent's turn

- **Given** the deterministic CLI has produced `.claude/skills/code-review/runs/<id>.json` with consolidated SARIF, metrics, and hotspots
- **When** the sub-agent processes the result
- **Then** within the same turn, the sub-agent reads the diff, reads the deterministic findings, and emits design-review findings of its own; no separate process is spawned to call the Anthropic API; no `claude -p` is invoked; the LLM call counts against the operator's interactive subscription session

### Scenario: LLM design review does not duplicate deterministic findings

- **Given** the deterministic SARIF contains a finding at `src/auth.py:47` for `python.lang.security.audit.sql-injection`
- **When** the sub-agent performs LLM design review
- **Then** its emitted design findings do not include a finding at `src/auth.py:47` for the same vulnerability class, measured as: 0 design findings whose `(file, line, CWE)` triple matches a deterministic finding within a ±3-line tolerance. The sub-agent's design-review prompt explicitly instructs against duplication

### Scenario: LLM design review surfaces issues the deterministic layer missed

- **Given** a fixture diff where the deterministic layer produces no findings but the diff contains a clear design issue (e.g., a function named `process_data` that actually handles authentication — a domain-naming mismatch)
- **When** the sub-agent performs LLM design review
- **Then** its emitted findings include at least one design finding flagging the naming/intent issue with `properties.category` in {`naming-intent`, `design`, `architecture`} and `ruleId` prefixed `llm-design.`

### Scenario: Design findings carry SDLC severity directly

- **Given** the sub-agent emits a design finding
- **When** the finding is structured
- **Then** the finding carries `properties.sdlc_severity` (one of `critical`, `important`, `minor`, `nit`) directly — no second pass through the aggregator's mapper is needed because the sub-agent's own prompt enforces the taxonomy when emitting findings

### Scenario: Critical and Important findings auto-spawn fix tasks per rule #25

- **Given** the consolidated review (deterministic + design) contains 2 Critical and 1 Important finding
- **When** the sub-agent processes the result
- **Then** 3 new fix-task artefacts are created in `/sdlc/work/active/` with ids following the `<parent-task-id>-fix1-<slug>` convention, each with `parent:` pointing to the parent story, `sources:` referencing the consolidated review file, and inserted at the front of the remaining task queue per the SDLC's auto-progress rules

### Scenario: Minor findings append to parent task notes, not as separate tasks

- **Given** the consolidated review contains 4 Minor findings
- **When** the sub-agent processes the result
- **Then** no new fix tasks are filed for the Minor findings; the parent task's `notes:` field gains 4 entries, each summarising one Minor finding with file:line and the rationale

### Scenario: Nit findings are dropped

- **Given** the consolidated review contains 7 Nit findings
- **When** the sub-agent processes the result
- **Then** no fix tasks are filed, the parent task's notes are not modified by Nit findings, and the sub-agent's report records the count for audit but takes no other action

### Scenario: The 2-round remediation bound (rule #25) holds

- **Given** a parent task's round-1 fix tasks have themselves produced Critical/Important findings on their own Review (round-2 fix tasks filed)
- **and Given** the round-2 fix tasks produce yet more Critical/Important findings on Review (would be round-3)
- **When** the sub-agent processes the round-3-would-be result
- **Then** the sub-agent halts the auto-progress loop, invokes the Autonomy gate's escalation interface, and reports to the operator with the option to iterate, accept as known debt, or rework the parent task — exactly as the current sub-agent does

### Scenario: Story-level review runs at story boundary with story-level scope

- **Given** the last task in a story has just closed cleanly
- **When** the SDLC loop reaches the story-boundary Review per the Execute verb's auto-progress logic
- **Then** the sub-agent invokes the CLI with `--scope story-level` and the cumulative story diff (base = story's first commit's parent, head = last task's commit); the CLI runs cross-task analyzers (dependency-cruiser at full scope, contract adapters from s4); design review for the cumulative diff happens in the same turn; fix tasks for story-level Critical/Important are filed under the same parent story

### Scenario: A CLI failure does not silently close a task

- **Given** the CLI exits non-zero (e.g., a required adapter was unreachable, or the worktree was malformed)
- **When** the sub-agent reads the output
- **Then** the sub-agent does not mark the task `done`, does not advance auto-progress, surfaces the failure via the Autonomy gate's escalation interface (per rule #14: never bypass the gate), and records the failure context (CLI exit code, which analyzer failed, what the error was) in `STATE.md`

### Scenario: Sub-agent runs cleanly under the operator's sandbox

- **Given** the operator's Claude Code session has `/sandbox` enabled in auto-allow mode with the recommended strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`)
- **When** the sub-agent is dispatched for a per-task review
- **Then** every Bash command the sub-agent runs (`python -m code_review.cli --capabilities`, the main `python -m code_review.cli ... --output ...` invocation, and the read of the output file) completes inside the sandbox without prompting the operator for filesystem or network widening; no `dangerouslyDisableSandbox` retry occurs; no fallback to unsandboxed execution is needed

### Scenario: Sub-agent refuses to retry failed commands unsandboxed

- **Given** a Bash command issued by the sub-agent fails with a sandbox-related error (e.g., bubblewrap's "operation not permitted", Seatbelt's deny, or a host-not-allowed network error)
- **When** Claude Code offers the sub-agent the option to retry with `dangerouslyDisableSandbox: true`
- **Then** the sub-agent's prompt explicitly forbids this retry — it does not invoke the escape hatch, even if doing so would let it complete the task. It surfaces the original failure to the operator via the Autonomy gate, naming what was blocked and what `settings.json` change would unblock it (e.g., "Schemathesis target `http://api.internal:8080` was blocked by the sandbox network policy. Add it to `sandbox.allowedDomains` and re-run.")

### Scenario: Context budget is respected on large story-level diffs

- **Given** a story-level diff containing 40+ changed files and 2000+ changed lines
- **When** the sub-agent runs the consolidated review
- **Then** the deterministic CLI completes within its own timeouts (orthogonal to context budget), and the LLM design review step either (a) completes successfully within the sub-agent's turn, or (b) emits a clear "context budget pressure" diagnostic and escalates to the operator suggesting the design review be re-dispatched as its own sub-agent. The sub-agent does not silently truncate the design review

### Scenario: No edits to /sdlc/SDLC.md are required for this story

- **Given** the integration is complete and tested
- **When** I `git diff /sdlc/SDLC.md` between before and after this story
- **Then** the diff is empty; only `.claude/agents/reviewer.md`, `.claude/skills/code-review/`, and possibly `CLAUDE.md`'s reviewer pointer have changed

### Scenario: Scope switch is instant and reversible

- **Given** a project running with `review_scope = "standard"` in the SDLC skill's config
- **When** the operator changes the config to `review_scope = "lite"` (or `"full"`)
- **Then** the next SDLC Review dispatch uses the corresponding scope; at `lite`, no deterministic CLI is invoked; at `full`, contract-testing adapters are included at story-level timing; no artefacts beyond the config need changing

### Scenario: `lite` scope matches the current SDLC reviewer's behaviour

- **Given** the `code-review` skill is installed but `review_scope = "lite"`
- **When** the SDLC loop dispatches the Review sub-agent for a per-task review
- **Then** the sub-agent does LLM-only review without invoking `python -m code_review.cli`; the output is functionally equivalent to the SDLC reviewer's behaviour before this epic existed; no deterministic findings appear; review speed is the same as before

## Test specification

- **Sub-agent invocation test** — given a fixture diff and a stub CLI that returns canned consolidated output, assert the sub-agent's dispatch produces the expected fix-task files with the right ids and parents.
- **Capability-check test** — fake `--capabilities` output with a policy-required analyzer marked `unavailable`; assert sub-agent escalates rather than submits a review with silent omission.
- **Design-finding fixture test** — small fixture diff with a known naming mismatch that no deterministic rule will catch; run a real sub-agent dispatch end-to-end; assert at least one design finding in the expected category appears.
- **Dedup-against-deterministic test** — fixture where deterministic SARIF contains a SQL-injection finding at a known line; run the sub-agent; assert no design finding duplicates that location/CWE within tolerance.
- **Severity routing test** — table-driven over the four SDLC severities × expected sub-agent action (file fix task / append to notes / drop / escalate).
- **Rule #25 bound test** — simulate round-1 → round-2 → round-3-would-be, assert escalation rather than silent round-3 filing.
- **CLI-failure test** — mock CLI to exit non-zero, assert sub-agent escalates via the Autonomy gate and does not close the task.
- **Sandbox-clean-run test** — run a full per-task review at `standard` scope in a `/sandbox`-enabled session with strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`); assert successful completion with no permission prompts and no unsandboxed fallback.
- **Sandbox-bypass-refusal test** — simulate a Bash command failing with a bubblewrap "operation not permitted" error during a sub-agent dispatch; assert the sub-agent escalates with a remediation message rather than retrying with `dangerouslyDisableSandbox: true`.
- **Scope-dispatch test (lite)** — set `review_scope = "lite"` in a fixture SDLC config; run a Review; assert no `python -m code_review.cli` subprocess was spawned; assert LLM-only findings appear.
- **Scope-dispatch test (standard)** — set `review_scope = "standard"`; run a Review; assert the CLI was invoked with `--review-scope standard`; assert security + quality findings appear; assert no coupling/cohesion or contract-testing findings appear.
- **Scope-dispatch test (full)** — set `review_scope = "full"`; run a story-level Review; assert the CLI was invoked with `--review-scope full`; assert contract-testing and coupling/cohesion findings appear alongside security + quality.
- **Scope-switch test** — start at `standard`, switch to `lite`, run a Review (assert no CLI), switch to `full`, run a Review (assert full analyzer set). No artefacts touched between switches beyond the config line.
- **Story-level fixture test** — multi-task fixture with planted cross-task drift (e.g., inconsistent error handling across two files); assert story-level review at `standard` or `full` scope surfaces it where per-task reviews of either file alone would not.
- **Context-budget test** — fixture story-level diff sized close to the sub-agent's turn budget at `full` scope; assert either successful completion or a clean diagnostic escalation, never silent truncation.
- **End-to-end task close test** — run a real per-task Review at `standard` scope with deterministic + LLM design on a fixture diff with planted findings of all four severities; assert the resulting `/sdlc/work/active/` and `/sdlc/work/done/` states match expectations.
- **Subscription-pool assertion** — instrument the test environment to fail if any `ANTHROPIC_API_KEY` is set or if `claude -p` is invoked during a Reviewer dispatch at any scope.
- **No-SDLC-diff assertion** — automated check in CI: any PR that modifies `.claude/agents/reviewer.md` or files under `.claude/skills/code-review/` must NOT modify `/sdlc/SDLC.md`. Cross-cutting changes (if any) require a separate ADR.


## Out of scope (deferred)

- A Verifier counterpart that consumes deterministic findings — Verifier remains a sub-agent producing Decision-shaped output as the SDLC document already describes; a future epic could give it a similar deterministic layer if useful.
- Unattended / CI invocation of the Reviewer — that would mean using the Agent SDK credit pool or an API key, which this epic explicitly avoids. A separate future epic could add a thin CI wrapper if needed.
- Concurrent reviews — the sub-agent's turn is single-threaded; the SDLC's auto-progress loop is also single-threaded.
- A web UI for browsing past reviews — out of scope; filesystem is the source of truth per SDLC line 10.
- Prompt iteration based on operator feedback — a structured feedback loop on the design-review prompt is a future epic.

---

