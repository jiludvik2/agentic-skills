---
id: s5-review-selection-scheme
kind: story
project: code-review
status: active
parent: epic-reviewer-subagent
sources: [adr-0010-split-deterministic-and-probabilistic-skills.md, adr-0011-review-selection-model.md]
created: 2026-05-28
updated: 2026-05-28
---

# s5 — Review-selection scheme

> **Note.** This story supersedes the retired `s5-subagent-integration-and-design-review` (moved to `done/` with a "retired" marker). The integration/consumer content of the old s5 moves to a separate future project; its requirements are captured in `sdlc/docs/strategy/intent-review-requirements.md`. See ADR-0010 for the split and ADR-0011 for the selection model adopted here.

## Summary

Encode a hierarchical review taxonomy (3 domains → subcategories → tools) and an orthogonal binary depth tier (`quick` / `full`) in `code_review/capabilities.json` (+ its schema), and wire two CLI flags — `--review` and `--depth` — to a deterministic resolution rule. This replaces the orphaned `--review-scope` flag with a data-driven, testable selection model that supports both granular per-subcategory invocations and broad domain/depth shortcuts, including standalone `--depth quick` / `--depth full` whole-codebase reviews.

## Use Case

- **As a** caller of `code-review` — CI, a human at the terminal, or a downstream consumer LLM
- **I want to** invoke "a quick security review," "a full review of coupling," or "a whole quick review" with one flag combination
- **so that** I get the right analyzer set for the situation without enumerating tool names, and any caller (deterministic CI or judgment-based LLM) shares the same simple surface.

## Locked taxonomy (requirements)

The review-selection surface defines three **domains**, each composed of one or more **subcategories**, an orthogonal binary **depth tier** (`quick` | `full`), per-subcategory **language coverage**, and per-subcategory **timing constraints**:

| Domain | Subcategory | Tier | Languages | Timing |
|---|---|---|---|---|
| `security` | `vulnerabilities` | quick | py, js, ts | any |
| `security` | `secrets` | quick | py, js, ts | any |
| `security` | `dependencies` | full | py, js, ts | any |
| `maintainability` | `complexity` | quick | py | any |
| `maintainability` | `dead-code` | quick | py, js, ts | any |
| `maintainability` | `duplication` | quick | js, ts | any |
| `maintainability` | `quality` | quick | js, ts | any |
| `maintainability` | `coupling` | full | py, js, ts | any |
| `maintainability` | `cohesion` | full | py | any |
| `contracts` | `conformance` | full | API | story-level |

> **Tool mapping is an implementation concern**, not part of this user contract. The current subcategory → analyzer mapping is recorded in **ADR-0011 § Subcategory → tool mapping**. A tool may be added, swapped, or removed within a subcategory without changing this story's requirements; only `capabilities.json` and ADR-0011's mapping table change.

## Resolution precedence (the contract)

1. **`--analyzer X`** (repeatable) overrides all selection flags — runs exactly those analyzers.
2. **`--review <domain>`** + `--depth` (default `quick`) — runs the union of subcategories whose `tier ≤ --depth` (`quick ⊆ full`).
3. **`--review <subcategory>`** — runs exactly that subcategory's analyzer(s); `--depth` is **ignored**.
4. **`--depth quick|full`** alone (no `--review`) — runs every analyzer at that tier across all domains.
5. **No selection flags** — defaults to `--depth quick`.
6. **Multiple `--review` values** are unioned (mix of domains and subcategories OK).
7. The resolved set is filtered by **diff languages**, the **`--scope`** timing gate (story-level-only analyzers excluded at per-task), and **`disabled_analyzers`** in `code-review.toml`.

## Acceptance Criteria

### Scenario: domain selection runs the domain's tier

- **Given** `--review security` and no explicit `--depth` (defaults to `quick`)
- **When** the CLI resolves the analyzer set
- **Then** it selects exactly: semgrep, bandit, gitleaks (the quick subcategories of `security`)
- **And** `--review security --depth full` additionally selects trivy.

### Scenario: subcategory selection runs exactly that subcategory, regardless of depth

- **Given** `--review secrets` with any `--depth` value (or none)
- **When** the CLI resolves
- **Then** it selects exactly gitleaks; `--depth` is ignored for subcategory selection.
- **And** `--review coupling` selects pydeps and dependency-cruiser even with the default `--depth quick` — because subcategory selection is depth-independent.

### Scenario: standalone depth runs the whole tier across all domains

- **Given** `--depth quick` with no `--review`
- **When** the CLI resolves
- **Then** it selects: semgrep, bandit, gitleaks, radon, vulture, knip, jscpd, eslint.
- **And** `--depth full` with no `--review` selects every analyzer (subject to language and timing filters).

### Scenario: default behaviour with no selection flags is a quick whole review

- **Given** no `--review`, no `--depth`, no `--analyzer`, with a target/diff supplied
- **When** the CLI is invoked
- **Then** it behaves as if `--depth quick` was passed (the whole quick set, after language filtering).

### Scenario: explicit `--analyzer` overrides domain/depth selection

- **Given** `--analyzer semgrep --review maintainability --depth full`
- **When** the CLI resolves
- **Then** only semgrep runs; `--review`/`--depth` are ignored.

### Scenario: multiple `--review` values are unioned

- **Given** `--review complexity --review coupling`
- **When** the CLI resolves
- **Then** the set is the union of those subcategories' tools: radon, pydeps, dependency-cruiser. Mixing domain + subcategory names is also valid (e.g. `--review security --review coupling`).

### Scenario: language filtering trims the resolved set per diff

- **Given** a diff containing only Python files
- **When** `--review security --depth quick` resolves
- **Then** the runnable set is: semgrep, bandit, gitleaks (eslint excluded — js/ts-only; trivy excluded — full tier).

### Scenario: story-level-only analyzers are gated by `--scope`

- **Given** `--review conformance --scope per-task`
- **When** the CLI resolves
- **Then** schemathesis is excluded (conformance is story-level-only); the resulting set for this subcategory is empty and the CLI exits non-zero with a clear message naming the `--scope story-level` requirement.
- **And** `--review conformance --scope story-level` selects schemathesis.

### Scenario: `--review contracts --depth quick` is an explicit empty with a clear message

- **Given** `--review contracts --depth quick`
- **When** the CLI resolves
- **Then** the set is empty; the CLI exits non-zero with a clear message: `"domain 'contracts' has no quick-tier analyzers; use --depth full"`.

### Scenario: unknown `--review` value errors with valid options

- **Given** `--review bogus`
- **When** the CLI parses arguments
- **Then** it exits non-zero with a clear error listing the valid domain names (`security`, `maintainability`, `contracts`) and the valid subcategory names from the taxonomy.

### Scenario: capabilities are self-describing

- **Given** `python -m code_review.cli --capabilities`
- **When** the output is inspected
- **Then** every analyzer entry declares `domain`, `subcategory`, and `tier`; the JSON validates against `code_review/schemas/capabilities.json`; the schema's enum constrains `domain` to {`security`, `maintainability`, `contracts`} and `tier` to {`quick`, `full`}.

### Scenario: eslint is no longer a security reviewer

- **Given** the updated capabilities + resolution
- **When** `--review security --depth full` runs against a JS/TS diff
- **Then** eslint is not in the selected set (JS/TS vulnerability coverage is via semgrep). eslint is reachable only via `--review maintainability` (or `--review quality`).

### Scenario: the old `--review-scope` flag is gone

- **Given** an invocation with `--review-scope standard`
- **When** the CLI parses arguments
- **Then** it errors with the standard Typer "no such option" message (the flag and its enum are removed).

## Test specification

- **`test_review_selection_resolution.py`** (new) — table-driven over the resolution precedence: each AC scenario above corresponds to one or more cases (domain@tier sets; subcategory exact; standalone depth; default quick; `--analyzer` override; union of multiple `--review`; story-level gate; contracts/quick empty; unknown value error).
- **`test_capabilities.py`** — extend: every analyzer entry has `domain`, `subcategory`, `tier`; the schema validates; enums are enforced; the taxonomy in the entries matches the locked table.
- **`test_scope_dispatch.py`** — remove/update the cases that asserted `--review-scope` flow + the bundled-reviewer content (the latter goes in Phase 3 with the consumer removal); keep the `--scope` timing tests.
- **`test_capabilities_runtime.py`** — adjust the comment that refers to `--review-scope` value acceptance/rejection.
- **Language-filter test** — confirm Python diff trims to py-eligible analyzers; JS/TS diff trims accordingly.
- **Negative tests** — invalid `--review` value, `contracts --depth quick`, `conformance --scope per-task`, each with the expected error message substring.

## Out of scope (deferred to other projects)

- **Reviewer sub-agent / consumer integration** — the LLM that invokes `code-review` and a probabilistic skill, dedups across them, and routes fix-tasks. Moved to a future consumer project per ADR-0010.
- **Probabilistic / LLM design-review skill** — moved to `intent-review` (separate sibling subdir, separate project) per ADR-0010. Requirements in `sdlc/docs/strategy/intent-review-requirements.md`.
- **Cross-skill aggregation / dedup** — explicitly not built (ADR-0010). A consumer LLM dedups by judgment.
- **`[scope_overrides]`** in `code-review.toml` — an advanced escape hatch mentioned in the architecture; not implemented in this story.
- **A third depth tier** (à la CodeQL's `security-and-quality`) — two tiers (`quick`/`full`) are sufficient for the current toolset; revisit if needed.
