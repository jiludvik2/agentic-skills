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

## Context

The CLI carried an orphaned `--review-scope {lite,standard,full}` flag — parsed but never wired to analyzer selection (the analyzer set came only from `--analyzer` / `--language`). The unified-reviewer epic, before the split (ADR-0010), had assumed coarse `lite/standard/full` bundles per ADR-0004; the operator rejected those bundle names as opaque and required:

- **Granular selection** by kind of review (not three coarse buckets).
- **A depth/extent axis** kept orthogonal to it.
- **Standalone entry points** — `--depth quick` and `--depth full` invocations that need no domain or subcategory.
- **Data-driven, CLI-resolved** — the mapping in JSON, resolved by Python (deterministic, testable); not interpreted by a prompt.

The split (ADR-0010) makes `code-review` a standalone deterministic skill with no LLM inside, which fixes the resolution location: it must be in the CLI. A prompt-based mapping would break standalone `--depth quick` / `--depth full` invocations.

Industry research across SonarQube, CodeQL/GHAS, Semgrep, Coverity, Fortify, Snyk, Checkmarx One, Veracode, Codacy, and DeepSource confirms two consistent patterns: **functionality is selected via a named curated rule-group** (Quality Profile / query suite / ruleset / preset / Rulepack / Analyzer); **depth is one of three mechanisms** — (a) bigger rule/query suite, (b) incremental-vs-full code scope, (c) engine precision/time budget. `code-review` already exposes mechanism (b) as `--scope per-task|story-level`; mechanism (c) is mostly N/A for off-the-shelf tools. Mechanism (a) — breadth-as-depth — is what `--depth quick|full` becomes.

## Decision

Adopt a **two-level taxonomy** with an **orthogonal binary depth tier**.

### Structure

- **Three domains** — `security`, `maintainability`, `contracts` — each containing one or more **subcategories** (the granular review types). Each subcategory maps to one or more analyzers.
- Each analyzer is tagged in `capabilities.json` with exactly one **domain**, one **subcategory**, and one **tier** (`quick` | `full`).
- The CLI exposes `--review` (repeatable; accepts either a *domain* name or a *subcategory* name) and `--depth {quick,full}` (default `quick`).
- The `--scope per-task|story-level` timing axis stays as-is (orthogonal; gates story-level-only analyzers like schemathesis).

### Locked taxonomy

| Domain | Subcategory | Tools | Tier | Languages | Timing |
|---|---|---|---|---|---|
| `security` | vulnerabilities | semgrep, bandit | quick | py, js, ts | any |
| `security` | secrets | gitleaks | quick | py, js, ts | any |
| `security` | dependencies | trivy | full | py, js, ts | any |
| `maintainability` | complexity | radon | quick | py | any |
| `maintainability` | dead-code | vulture, knip | quick | py, js, ts | any |
| `maintainability` | duplication | jscpd | quick | js, ts | any |
| `maintainability` | quality | eslint | quick | js, ts | any |
| `maintainability` | coupling | pydeps, dependency-cruiser | full | py, js, ts | any |
| `maintainability` | cohesion | cohesion | full | py | any |
| `contracts` | conformance | schemathesis | full | API | story-level |

### Resolution precedence (deterministic, implemented in `cli.py`)

1. **`--analyzer X`** (repeatable) overrides everything else — runs exactly those analyzers.
2. **`--review <domain>`** + `--depth tier` — runs all subcategories of the domain whose tier ≤ requested tier (`quick` ⊆ `full`). `--depth` defaults to `quick`.
3. **`--review <subcategory>`** — runs exactly that subcategory's analyzer(s); `--depth` is **ignored** for subcategory selection.
4. **`--depth quick|full`** alone (no `--review`) — runs every analyzer at that tier across all domains (the standalone quick/full review).
5. **No selection** — defaults to `--depth quick`.
6. **Multiple `--review` values** are unioned.
7. The resolved set is then filtered by **diff languages** (per the existing `lang_select` machinery), the **`--scope` timing gate** (story-level-only analyzers excluded at per-task), and **`disabled_analyzers`** from `code-review.toml`.

### Cleanups

- The orphaned `--review-scope` flag and `ReviewScope` enum are **removed** from `cli.py`.
- The `review_scope` property is **removed** from `capabilities.json` (currently only on the schemathesis entry) and from `schemas/capabilities.json`.
- `eslint`'s `rule_classes` drops `security` and retains only `quality`. JS/TS vulnerability coverage is via semgrep.
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
