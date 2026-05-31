---
id: adr-0011-review-selection-model
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [s5-review-selection-scheme.md, adr-0010-split-deterministic-and-probabilistic-skills.md, adr-0004-three-review-scopes.md, capabilities.json]
created: 2026-05-28
updated: 2026-05-28
---

# ADR-0011 — Hierarchical review selection (domain → subcategory) with orthogonal quick/full depth

> **Amended by [ADR-0021](../../work/active/adr-0021-remove-schemathesis-from-scope.md) (2026-05-31).** The `contracts` review domain and its `conformance` subcategory were removed when Schemathesis was dropped from code-review. Every reference below to **`contracts`**, **`conformance`**, the **`schemathesis`** analyzer, the **`contract-verification`** review-kind, and the **story-level-only** gating that existed solely for it is **historical** — the selection model itself (domain → subcategory, orthogonal quick/full depth, `--scope` timing) is unchanged and still live for the remaining `security` / `maintainability` domains. The `review_scope`-property removal (below) did land.

## Context

The CLI carried an orphaned `--review-scope {lite,standard,full}` flag — parsed but never wired to analyzer selection (the analyzer set came only from `--analyzer` / `--language`). The unified-reviewer epic, before the split (ADR-0010), had assumed coarse `lite/standard/full` bundles per ADR-0004; the operator rejected those bundle names as opaque and required:

- **Granular selection** by kind of review (not three coarse buckets).
- **A depth/extent axis** kept orthogonal to it.
- **Standalone entry points** — `--depth quick` and `--depth full` invocations that need no domain or subcategory.
- **Data-driven, CLI-resolved** — the mapping in JSON, resolved by Python (deterministic, testable); not interpreted by a prompt.

The split (ADR-0010) makes `code-review` a standalone deterministic skill with no LLM inside, which fixes the resolution location: it must be in the CLI. A prompt-based mapping would break standalone `--depth quick` / `--depth full` invocations.

Industry research across SonarQube, CodeQL/GHAS, Semgrep, Coverity, Fortify, Snyk, Checkmarx One, Veracode, Codacy, and DeepSource confirms two consistent patterns: **functionality is selected via a named curated rule-group** (Quality Profile / query suite / ruleset / preset / Rulepack / Analyzer); **depth is one of three mechanisms** — (a) bigger rule/query suite, (b) incremental-vs-full code scope, (c) engine precision/time budget. `code-review` already exposes mechanism (b) as `--scope per-task|story-level`; mechanism (c) is mostly N/A for off-the-shelf tools. Mechanism (a) — breadth-as-depth — is what `--depth quick|full` becomes.

## Decision

Adopt a **two-level taxonomy** (domains containing subcategories) with an **orthogonal binary depth tier**, and a per-subcategory analyzer assignment.

The taxonomy values themselves — the specific domain names, subcategory names, tier assignments, language coverage, timing constraints — are the **user-facing contract** specified as requirements in **`s5-review-selection-scheme.md`**. This ADR records the **design decisions** that implement that contract, including the subcategory → analyzer mapping (which is implementation, not requirement).

### Design decisions

- **Taxonomy structure: two levels + orthogonal depth.** Domains group related subcategories; subcategories are the granular review types; tier is a per-subcategory tag, orthogonal to domain. This shape balances coarse "give me a security review" shortcuts with fine "just check coupling" precision. Three alternative shapes were considered (see § Alternatives).
- **Mapping data lives in `capabilities.json`.** Each analyzer entry is tagged with `domain`, `subcategory`, and `tier`. The CLI reads these tags at startup and resolves `--review`/`--depth` against them. The mapping is data, not prompt prose — testable with pytest, mutable without code changes.
- **Resolution runs in the CLI** (Python, deterministic). Not in a prompt artefact: per ADR-0010, `code-review` has no LLM inside it, so a prompt-based mapping would break standalone `--depth quick` / `--depth full` invocations and lose pytest-testability. The full resolution precedence is specified as ACs in `s5-review-selection-scheme.md`; this ADR deliberately does not duplicate them.
- **Subcategory selection ignores `--depth`.** If a caller asks for a specific subcategory (e.g. `--review coupling`), they receive that subcategory's analyzers regardless of its tier. Depth gates only domain-level and standalone selections. Rationale: a caller naming a subcategory has been explicit; a depth filter overriding that would surprise.
- **The `--scope` timing axis stays orthogonal.** Story-level-only analyzers (currently `schemathesis`) are gated by `--scope story-level` regardless of `--review`/`--depth`. This keeps the three industry depth mechanisms cleanly separated: breadth (`--depth`), incremental-vs-cumulative scope (`--scope`), engine precision (not exposed; mostly N/A for off-the-shelf tools).

### Subcategory → tool mapping (implementation)

This table is the implementation detail the s5 user contract abstracts over. A subcategory's tool set may change — add, swap, or remove — without touching the user contract in s5; only `capabilities.json` and this table change. A subcategory's tier and language coverage in s5 follow from the union of its tools' attributes.

| Subcategory | Tool(s) |
|---|---|
| `vulnerabilities` | semgrep, bandit |
| `secrets` | gitleaks |
| `dependencies` | trivy |
| `complexity` | radon |
| `dead-code` | vulture, knip |
| `duplication` | jscpd |
| `quality` | eslint |
| `coupling` | pydeps, dependency-cruiser |
| `cohesion` | cohesion |
| `conformance` | schemathesis |

### Cleanups

- The orphaned `--review-scope` flag and `ReviewScope` enum are **removed** from `cli.py`.
- The `review_scope` property is **removed** from `capabilities.json` (currently only on the schemathesis entry) and from `schemas/capabilities.json`.
- `eslint`'s `rule_classes` drops `security` and retains only `quality`. JS/TS vulnerability coverage is via semgrep — this is the one tool-mapping consequence of the design that the s5 ACs depend on, so it's noted here as a coordinated change.
- ADR-0004 ("three review scopes: lite/standard/full") is **superseded** by this ADR for `code-review`'s selection surface. (Lite/standard/full as operator-facing scopes survive only in any future consumer that maps them to `--review`/`--depth` invocations of `code-review`.)

## Consequences

- `code-review` is **fully self-describing**: `--capabilities` exposes the taxonomy; the CLI resolves it; any caller (human, CI, future consumer LLM) uses the same flags.
- The mapping is **data, not prompt prose** — testable with pytest, mutable without code changes, no LLM interpretation cost.
- `--depth` in `code-review` is honestly **breadth-as-depth** (more analyzers at `full`), matching the industry's pattern (a) — CodeQL's `default → security-extended → security-and-quality` is the canonical precedent.
- `contracts › conformance` requires both `--depth full` and `--scope story-level` to run; other combinations produce a **clear empty-set message**, never silently nothing.
- `--review` accepts both domain and subcategory names, drawn from the same flat namespace. Names are checked at parse time; unknown values produce a clear error listing valid options.

## Alternatives considered

1. **Three coarse bundles** (`standard` / `full` / lite — the original ADR-0004 design). Rejected by the operator as opaque and not granular.
2. **Flat granular categories** (just the rule_classes — security, secrets, complexity, dead-code, …). Rejected: too many tools mash under `security`, no shortcut for "give me a security review."
3. **Per-analyzer depth tag applied uniformly**, with subcategory selection also gated by depth (so `--review coupling --depth quick` would yield empty since coupling tools are `full`). Rejected in favour of the current rule: **subcategory selection ignores `--depth`** — if you ask for a specific subcategory, you get it regardless of its tier.
4. **Mapping in a prompt artefact** (`reviewer.md` / `SKILL.md`) interpreted by an LLM. Rejected: breaks standalone `--depth quick`/`--depth full` (no LLM inside `code-review` after the split), loses determinism + testability, burns tokens on a mechanical lookup.
5. **Folding depth into `--scope`** (one axis for both incremental-vs-full and breadth). Rejected: conflates two distinct industry mechanisms; `--scope` stays as timing/incremental-vs-full only.

## Status

Accepted 2026-05-28. Implementation specified by `s5-review-selection-scheme.md`.
