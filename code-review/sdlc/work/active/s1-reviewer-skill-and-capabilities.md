---
id: s1-reviewer-skill-and-capabilities
kind: story
project: code-review
status: active
parent: epic-reviewer-subagent
children: [s1-t0-skill-scaffold-and-schemas, s1-t1-capabilities-json-content, s1-t2-capabilities-runtime-introspection, s1-t3-setup-script, s1-t4-reviewer-scope-integration]
created: 2026-05-26
updated: 2026-05-26  # scope model: single reviewer, lite/standard/full scopes; plan approved
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
