---
id: architecture-reviewer-subagent
kind: architecture
project: code-review
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-28  # ADR-0010 / ADR-0011: sub-agent integration retired; review-selection (domain/subcategory/depth) replaces lite/standard/full. §5 + §8 + §17.5/17.6 carry supersede notes; load-bearing sections (Analyzer Protocol, SARIF, sandbox, severity, dedup) unchanged.
verified-on: 2026-05-28
tags: [reviewer, architecture, sarif, deterministic-analyzer, python, uv, sandbox]
---

# Architecture: Reviewer Sub-agent with Deterministic Analyzer Layer

This document is the single architectural reference for the work decomposed in `epic-reviewer-subagent` (stories s0–s5). It covers module layout, data flow, the Analyzer Protocol, output shape, dedup and severity logic, sub-agent integration mechanics, security and license posture, the uv-based build and dev workflow, the constraints the Claude Code sandbox imposes on every part of the design, and the contract surface this architecture depends on from the upstream SDLC skill. The two governance-risk mitigations agreed during tool-stack review (pin versions, keep pip fallback working) are baked into the build setup. Sandbox compatibility is a first-class constraint — see §16. SDLC-skill compatibility is treated as stable by convention, with the contract surface enumerated in §17.

This is a steady-state architecture document. Implementation tasks are not pre-decomposed — task breakdown happens at Plan time per the SDLC's Plan verb. Where this document and a story disagree, the story is canonical; please update this document when a story changes.

> **Superseded in part — split into deterministic + probabilistic skills (ADR-0010, 2026-05-28) and review-selection scheme replaces three scopes (ADR-0011, 2026-05-28).** The `code-review` skill is now a **pure deterministic analyzer**: no LLM call inside, no `reviewer` sub-agent installed by `setup.sh`, no `review_scope` config key. The LLM design-review work moves to a sibling `intent-review` project. Section-level impact:
> - **§5 (Data flow)** — the `--review-scope` flag is gone; the CLI takes `--review <domain|subcategory>` (repeatable) + `--depth <quick|full>` per ADR-0011. The CLI is still invoked by a consumer (CI, a human, or `intent-review`), but not by a sub-agent that this skill installs.
> - **§8 (Sub-agent integration)** — *entirely superseded*. The retired flow was: sub-agent reads `review_scope`, branches on `lite`/`standard`/`full`, invokes the CLI, runs LLM design review in the same turn, files fix tasks. None of this lives in `code-review` any more. Consumer responsibilities (reading SARIF, design review, fix-task routing) move to `intent-review` and to a future consumer LLM that may dedup across the two skills' outputs by judgment — see `sdlc/docs/strategy/intent-review-requirements.md`.
> - **§17.5 / §17.6 (`review_scope` config key + location)** — superseded. The skill has no project-level SDLC config key; the consumer drives selection via CLI flags.
> - **Load-bearing sections that survive unchanged:** §3 module layout, §9 concurrency/timeouts, §10 build, §11 security, §12 testing, §16 sandbox.
>
> **Superseded again — analyzer layer re-architected to a thin invocation runner (ADR-0020, 2026-05-31).** The SARIF-normalisation output contract described throughout this doc is **deleted**. The CLI no longer aggregates, dedups, severity-maps, or emits a SARIF envelope: `polyreview run` now collects one **raw `CaptureOutput`** per analyzer (verbatim stdout/stderr + an ADR-0019 `status`) into a **`ReviewBundle`** and emits `review-bundle.v1.json` directly, for the consuming agent to interpret. Section-level impact — **§4 Analyzer Protocol**: `run()` now returns `CaptureOutput`, not `AnalyzerOutput`/SARIF. **§5 Data flow / §6 SARIF + dedup + severity**: *entirely superseded* — `aggregator.py`, `severity.py`, `hotspots.py`, `adapters/sarif_utils.py`, `MetricSet`, and the `{sarif, metrics, ranked_hotspots, analyzers}` output document no longer exist; see `code_review/review_bundle.py` and `schemas/review-bundle.v1.json`. The only surviving SARIF use is *internal*: eslint/trivy emit tool-native SARIF on stdout that the runner captures **raw, unparsed**. References below to consolidated/deduped SARIF, `sdlc_severity` tagging, hotspot ranking, and the output envelope are historical.
>
> The original framing is preserved below — both the prose and the at-a-glance tables — because the bets that proved out (the Analyzer Protocol, SARIF + `sdlc_severity`, the sandbox-first design) carried directly into the deterministic-only shape. The supersede notes on §5 / §8 / §17.5–17.6 point readers at the current contracts (ADR-0011 for selection, ADR-0010 for the split).

> **Superseded in part — Pact dropped (ADR-0008, 2026-05-27).** Contract testing in this epic is now **Schemathesis only**. References to **Pact** below (a `pact.py` adapter, the `pact-broker-fixture/` docker-compose, broker auth, `requires_docker` markers, broker hosts in `allowedDomains`) are **retained as historical design context** and are **not** to be built. The at-a-glance structures (module tree, scope/severity/sandbox tables) have been trimmed to match; the surrounding prose has not. See `s4-contract-testing-adapters.md` and ADR-0008 for the authoritative scope.
>
> **Superseded — contract testing removed entirely (ADR-0021, 2026-05-31).** With the auth-redaction fork under the thin invocation runner (ADR-0020), Schemathesis and the entire `contracts` review domain were **removed from code-review**; contract testing moves to a **separate dedicated skill** (captured to `/sdlc/raw/`). Every **Schemathesis / contract-testing / `contract_testing` / `conformance` / `contracts`-domain** reference below — adapter, `schemathesis-target` fixture, the `contract-verification` review kind, the story-level-only scope wiring, the `full`-scope `allowedDomains` widening, the Schemathesis pin — is now **historical design context only** and **not** part of the shipping product. See **ADR-0021** for the authoritative scope.

## 1. Goals and Non-goals

### Goals

- Wrap a curated set of deterministic static-analysis tools (security, secrets, complexity, coupling, cohesion, duplication, dead-code, dependency-graph, contract testing) behind one Python CLI.
- Expose that CLI as a Claude Code skill called `code-review`, installable at `.claude/skills/code-review/`.
- Ship a single `reviewer` sub-agent (at `.claude/agents/reviewer.md`) that reads the SDLC skill's `review_scope` config (`lite` / `standard` / `full`), invokes the CLI with the appropriate scope, then performs LLM-based design review within the same sub-agent turn using deterministic findings as grounding context.
- Keep every LLM call inside the operator's interactive Claude Code session — zero use of `claude -p`, no Anthropic API key, no Agent SDK credit pool.
- **Run cleanly under the Claude Code sandbox** (auto-allow mode) with no `excludedCommands` entries, no `allowUnsandboxedCommands` fallback, and only documented, narrow widening of `allowedDomains` (at `full` scope for contract-test targets).
- Emit deduplicated SARIF 2.1.0 with findings tagged in the SDLC's severity taxonomy (Critical / Important / Minor / Nit).
- File `-fix<N>-` tasks for Critical and Important per rule #25 (2-round remediation bound), append Minor to the parent task's notes, drop Nit.
- **Give the operator one intuitive choice** — `review_scope` — that maps their project profile (PoC, simple production, complex brownfield) to the right analyzer set without per-tool configuration.

### Non-goals

- No HTTP service, no FastAPI, no async job queue.
- No git-worktree isolation, no result cache, no database. Filesystem is the only persistent store. All transient outputs are written inside the project's working directory (under `.claude/skills/code-review/runs/`) so they comply with the sandbox's CWD-only write default. SDLC artefacts go to `/sdlc/work/active/` and `/sdlc/work/done/` per the SDLC's existing file conventions.
- No unattended / CI invocation in this epic. A future epic could add a thin CI wrapper that uses the Agent SDK credit pool or an API key; not now.
- No multi-tenant, multi-repo, or multi-host concerns. Single operator, single repo per session.
- No service-style capability-discovery endpoints. Capability declaration is static metadata in `capabilities.json`.
- **No use of `/tmp`** for skill outputs or caches — `/tmp` is outside the sandbox's default writable region and would force every operator to widen `sandbox.filesystem.allowWrite`. All writes stay inside CWD.
- **No modification to the SDLC skill.** The `code-review` skill extends the `reviewer` sub-agent's capabilities. The SDLC skill is treated as an external dependency whose conventions (severity taxonomy, fix-task naming, autonomy gate) are stable. The only operator-visible coupling is the `review_scope` config key, which the SDLC skill is presumed to support.
- **No separate sub-agent files per scope.** One `reviewer.md` handles all three scopes via branching logic in its prompt; there are no `basic-reviewer.md` or `full-reviewer.md` files.
- **No SDLC-version check at runtime.** The architecture depends on the SDLC contract surface enumerated in §17, treated as stable by convention. There is no parser, no compatibility range, no refusal-to-load on unknown SDLC versions.

## 2. High-level shape

> **Superseded by ADR-0010 (2026-05-28).** The diagram below shows the retired sub-agent-inside-skill arrangement (`reviewer` sub-agent reads `review_scope`, invokes the CLI, performs LLM design review in the same turn). The current shape is: a consumer (CI, a human, `intent-review`) invokes `python -m code_review.cli` directly with `--review`/`--depth` flags per ADR-0011; the skill installs no sub-agent. The CLI half of the diagram (lower box: `code-review` skill) is unchanged and remains accurate.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Operator's interactive Claude Code session                           │
│                                                                      │
│  SDLC skill's Review verb dispatches the `reviewer` sub-agent.       │
│  The sub-agent reads the project's review_scope config:              │
│    - review_scope = "lite"       → LLM-only review (no CLI)         │
│    - review_scope = "standard"   → security + quality + LLM design  │
│    - review_scope = "full"       → standard + coupling + contracts   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ reviewer sub-agent (.claude/agents/reviewer.md)                │  │
│  │   1. Read spec/plan/diff                                       │  │
│  │   2. Read review_scope from SDLC config                        │  │
│  │   3. If lite: skip to step 6 (LLM-only)                       │  │
│  │   4. python -m code_review.cli --review-scope <scope> ...      │  │
│  │   5. Read .claude/skills/code-review/runs/<id>.json            │  │
│  │   6. LLM design review  ← THIS turn, interactive pool          │  │
│  │   7. Merge findings, apply severity routing                    │  │
│  │   8. File -fix<N>- tasks, append Minor to notes, drop Nit      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                  │                                  ▲
                  │ Bash subprocess (steps 4-5)      │ JSON file
                  │ (skipped at lite scope)           │
                  ▼                                  │
┌──────────────────────────────────────────────────────────────────────┐
│ code-review skill (.claude/skills/code-review/)                      │
│   code_review/ Python package, invoked as python -m code_review.cli  │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │ CLI (typer)                                                  │   │
│   │   └─→ adapter registry (explicit)                            │   │
│   │       └─→ asyncio.TaskGroup fan-out                          │   │
│   │           ├─→ Semgrep adapter   ──┐                          │   │
│   │           ├─→ Bandit adapter    ──┤                          │   │
│   │           ├─→ gitleaks adapter  ──┤                          │   │
│   │           ├─→ Trivy adapter     ──┤  per-adapter subprocess  │   │
│   │           ├─→ Radon adapter     ──┤  asyncio.create_subprocess_exec
│   │           ├─→ ESLint adapter    ──┤  bounded by asyncio.wait_for
│   │           ├─→ dep-cruiser ad.   ──┤                          │   │
│   │           ├─→ jscpd / vulture / knip / pydeps / cohesion     │   │
│   │           └─→ Schemathesis (story-level only)                │   │
│   │       └─→ aggregator (dedup, severity map, hotspots)         │   │
│   │       └─→ JSON output written atomically to --output         │   │
│   └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

Four things to note about this picture:

- The sub-agent and the CLI are in **the same process tree as the operator's Claude Code session**. The LLM design review at step 6 is a turn of that session.
- At **`lite` scope, the CLI is never invoked** — the sub-agent skips steps 4–5 and does LLM-only review, exactly matching the current SDLC reviewer's behaviour. The `code-review` skill is installed but inert. This is the zero-overhead path for PoC projects.
- At **`standard` and `full` scope**, the CLI fans out across the appropriate analyzer set (see §5 for the scope-to-analyzer mapping). The difference between `standard` and `full` is that `full` adds coupling/cohesion and contract testing.
- Every analyzer runs as a **subprocess**, invoked via `asyncio.create_subprocess_exec` from the CLI's event loop. The CLI never imports an analyzer as a Python library, except where the analyzer is itself a Python library (Bandit, Radon, vulture, **Schemathesis**). **Schemathesis (s4) is the exception that also performs network egress in-process** — run under a cooperative deadline via `asyncio.to_thread`, egress still gated by `sandbox.allowedDomains`; see **ADR-0009**.
- The CLI is **pure JSON in / JSON out**. It does not write to `/sdlc/work/active/` itself. The sub-agent files fix tasks; the CLI's only output is the consolidated review document.

## 3. Module layout

```
.claude/skills/code-review/
├── SKILL.md                      # human-readable description, invocation patterns
├── capabilities.json             # static metadata (review kinds, stack coverage,
│                                 # analyzer registry, taxonomies)
├── code-review.toml                 # operator-tunable config (disabled analyzers,
│                                 # dedup tolerance, severity overrides, hotspot weights)
├── pyproject.toml                # uv-managed, version-pinned, MIT
├── uv.lock                       # checked in
├── package.json                  # Node tooling for JS analyzers (ESLint, dep-cruiser, jscpd, knip)
├── package-lock.json             # checked in; deterministic install
├── README.md                     # quickstart for the operator
├── node_modules/                 # gitignored; populated by `npm ci` at skill setup time
├── runs/                         # gitignored; per-review consolidated JSON output
│                                 # (replaces /tmp/review-<id>.json from the pre-sandbox design)
├── cache/                        # gitignored; analyzer caches kept inside CWD per sandbox rules
│   ├── trivy-db/                 # pre-fetched vulnerability database
│   ├── semgrep-rules/            # pre-fetched Semgrep rule packs (when used)
│   ├── hypothesis/               # Schemathesis fuzzing state
│   └── raw/                      # adapter raw output (debug; post-secrets-redaction)
├── scripts/
│   ├── setup.sh                  # one-time install: uv sync, npm ci, pre-fetch caches
│   └── license_audit.py          # CI check: every dependency licensed under MIT/Apache/BSD
├── code_review/                     # Python package
│   ├── __init__.py
│   ├── cli.py                    # typer entry point; --capabilities, --scope, --diff, --output
│   ├── contracts.py              # Analyzer Protocol, AnalyzerOutput, MetricSet, ReviewRequest
│   ├── config.py                 # tomllib load of code-review.toml, validation against schema
│   ├── paths.py                  # resolve skill-relative paths (runs/, cache/, etc.)
│   ├── adapters/
│   │   ├── __init__.py           # explicit registry: name → adapter class
│   │   ├── base.py               # shared subprocess helpers, timeout machinery, env scrubbing
│   │   ├── semgrep.py
│   │   ├── bandit.py
│   │   ├── gitleaks.py
│   │   ├── trivy.py
│   │   ├── radon.py
│   │   ├── vulture.py
│   │   ├── pydeps.py
│   │   ├── cohesion.py
│   │   ├── jscpd.py
│   │   ├── eslint.py
│   │   ├── dep_cruiser.py
│   │   ├── knip.py
│   │   └── schemathesis.py       # story-level only
│   ├── aggregator.py             # dedup, hotspot scoring
│   ├── severity.py               # SDLC severity mapper, table-driven
│   ├── sarif.py                  # SARIF dict construction helpers
│   ├── diff.py                   # git diff parsing, language detection
│   └── logging.py                # stdlib logging + JSONFormatter wiring
└── schemas/
    ├── capabilities.json         # JSON Schema for the capabilities document
    ├── review-request.json       # JSON Schema for CLI inputs
    ├── review-response.json      # JSON Schema for CLI output (consolidated doc)
    └── sarif-2.1.0.json          # bundled SARIF spec for validation
tests/
├── conftest.py
├── fixtures/
│   ├── python-with-known-issues/        # known Semgrep, Bandit, Radon findings
│   ├── nextjs-with-known-issues/        # known ESLint, dep-cruiser, jscpd findings
│   ├── secrets-fixture/                 # known gitleaks finding
│   └── schemathesis-target/             # fixture FastAPI with planned spec drift
├── test_contracts.py
├── test_cli.py
├── test_aggregator.py
├── test_severity.py
├── test_sandbox_compatibility.py   # asserts no writes outside CWD, no network outside allowlist
├── test_adapters/                # one test module per adapter
└── test_subagent_integration.py  # exercises the sub-agent's invocation pattern via subprocess
```

Things to call out:

- **Package layout uses `code_review/` not the skill's name** — the Python package is what `python -m code_review.cli` resolves to, and giving it the skill's name (`code-review/`) would mean a hyphen in the import path, which Python forbids. The skill directory has a hyphen; the Python package inside it does not.
- **No `__init__.py` business logic.** Pure re-exports only.
- **Explicit adapter registry**, not entry-point auto-discovery. The registry in `code_review/adapters/__init__.py` maps string name → adapter class. Adding an adapter is one import and one dict entry. No magic.
- **Schemas are bundled, not fetched.** The skill works offline. SARIF 2.1.0's official schema (~600KB) is checked in at `schemas/sarif-2.1.0.json`.
- **`runs/`, `cache/`, and `node_modules/` all live inside the skill directory** — i.e. inside the project's CWD when the operator runs the sub-agent. This is the load-bearing decision for sandbox compatibility: the sandbox's default writable region is CWD only, and keeping every transient output here means the skill works without any `sandbox.filesystem.allowWrite` widening. The pre-sandbox draft of this architecture put outputs in `/tmp`; that doesn't work.
- **Node tooling is vendored**, not fetched at run time. `package.json` + `package-lock.json` are committed; `npm ci` is a one-time setup step that populates `node_modules/`. The CLI invokes JS analyzers as `node ./node_modules/.bin/<tool>`, never via `npx` (which would re-resolve from the registry and fail under sandbox).
- **A `paths.py` module resolves all skill-relative paths from a single anchor** so adapters never construct paths assuming a particular CWD layout. This also lets tests inject a temporary skill root.

## 4. The Analyzer Protocol

Defined in `code_review/contracts.py`:

```python
from typing import Protocol, Optional
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ReviewRequest:
    scope: str                      # "per-task" | "story-level" | "contract-verification"
    diff_range: Optional[str]       # e.g. "abc1234..def5678", None = whole repo
    target_paths: tuple[str, ...]   # paths to scope to (derived from diff)
    languages: frozenset[str]       # {"python", "typescript"} etc.
    config: dict                    # adapter-specific config from code-review.toml

@dataclass(frozen=True)
class MetricSet:
    per_file: dict[str, dict]       # file → {cc, mi, raw, ...}
    per_class: dict[str, dict]      # qualified name → {lcom4, ...}
    coupling: dict[str, dict]       # file → {fan_in, fan_out}

@dataclass(frozen=True)
class AnalyzerOutput:
    sarif: dict                      # SARIF 2.1.0 document (single run)
    metrics: Optional[MetricSet] = None
    duration_s: float = 0.0
    status: str = "ok"               # "ok" | "timeout" | "error" | "skipped"
    error: Optional[str] = None      # human-readable; None when status == "ok"
    raw_output_path: Optional[str] = None  # path to .claude/skills/code-review/cache/raw/<adapter>.<ext>, debug only

class Analyzer(Protocol):
    name: str                        # registry key, e.g. "semgrep"
    kind: str                        # "deterministic" | "deterministic-runtime" | "llm"
    default_timeout_s: int
    scope_restrictions: frozenset[str] = frozenset()  # {"story-level"} for contract adapters

    async def run(self, request: ReviewRequest) -> AnalyzerOutput: ...
```

Key shape decisions:

- **`async def run`** — every adapter is async, even those whose underlying tool is a one-shot subprocess. This lets the orchestrator use `asyncio.TaskGroup` uniformly and apply `asyncio.wait_for` for timeouts.
- **Frozen dataclasses** for inputs/outputs. Immutability simplifies test fixtures and rules out accidental sharing between concurrent adapter runs.
- **Status is a string enum**, not a boolean, because timeout and skipped are meaningfully different from ok and error.
- **No exception propagation through the Protocol.** Adapters catch their own errors and report them via `status` + `error`. A crashing adapter does not kill the CLI; it produces an output with `status="error"` and the rest of the run completes.

## 5. Data flow

> **Superseded in part by ADR-0011 (2026-05-28).** The flow below shows `--review-scope <lite|standard|full>` invocations from a `reviewer` sub-agent. The current CLI takes `--review <domain|subcategory>` (repeatable) and `--depth <quick|full>`, and is invoked by any consumer — there is no sub-agent installed by this skill. **The aggregator, dedup, severity-mapping, and output-shape steps (5.x's downstream) were since DELETED by ADR-0020 (see the top-of-doc banner): the CLI now emits a raw `review-bundle.v1.json`, not a SARIF envelope.**

### 5.1 Per-task review (the common case)

```
Sub-agent decides to invoke a per-task review.

  ↓

1. Sub-agent runs:
     python -m code_review.cli --capabilities
   to check that policy-required analyzers (e.g. gitleaks) are
   `status: available`. Escalates via Autonomy gate if not.

  ↓

2. Sub-agent runs:
     python -m code_review.cli \
       --scope per-task \
       --diff abc1234..def5678 \
       --output .claude/skills/code-review/runs/<task-id>.json
   via the Bash tool.
   (The `--output` argument is resolved relative to CWD. Writing
   inside the skill directory keeps the operation inside the
   sandbox's default writable region.)

  ↓

3. CLI parses --diff, asks git for the touched file list, computes
   per-file language, derives the default analyzer set (per
   capabilities.json) intersected with non-disabled analyzers
   (per code-review.toml).

  ↓

4. CLI starts asyncio.TaskGroup:
   - one task per active adapter
   - each adapter wrapped in asyncio.wait_for(default_timeout_s)
   - each adapter runs its subprocess with create_subprocess_exec
   - on timeout: process-group kill, status="timeout"
   - on non-zero exit (and not timeout): status="error",
     stderr captured to AnalyzerOutput.error

  ↓

5. CLI hands per-adapter AnalyzerOutput list to aggregator.

  ↓

6. Aggregator:
   - extracts all SARIF `result` entries with provenance (which adapter)
   - groups by (file, line ±line_tolerance, CWE) — see §6
   - merges groups: highest severity wins, sources list populated
   - applies severity mapper (table from code-review.toml or default)
   - computes hotspot composite score per file (weighted by
     finding severity, complexity, fan-in+fan-out, inverse LCOM4)

  ↓

7. CLI builds the consolidated document (review-response shape, §7),
   writes to `<output>.tmp` in the same directory as `<output>`,
   then os.rename → final path. The `.tmp` sibling pattern keeps
   atomicity within one filesystem and one sandbox-writable region.
   stdout: one line summary (`analyzers: 8 | findings: 14 | duration: 41.2s`).
   Exit code: 0 if all analyzers ok or only timeouts; non-zero if any
   adapter status=="error".

  ↓

8. Sub-agent reads the output JSON, performs the LLM design-review
   step in the same turn (§9), merges design findings into the
   review object, then routes findings per §8.
```

### 5.2 Story-level review

Same flow as 5.1 with three differences:

- `--scope story-level` includes contract-testing adapters (Schemathesis, Pact).
- The diff range is the cumulative story diff (`<story-first-commit>^..<last-task-commit>`).
- Hotspot scoring may include files not directly modified — cross-task patterns surface here that per-task scopes miss.

### 5.3 Capabilities check

Independent flow, runs against an empty diff:

```
1. Sub-agent runs:  python -m code_review.cli --capabilities

  ↓

2. CLI loads capabilities.json (static), then runs runtime
   availability check per adapter:
   - subprocess `<tool> --version` with 5s timeout
   - or `which <tool>` for binaries
   - or import check for Python-library adapters

  ↓

3. CLI emits combined static+runtime JSON to stdout. Sub-agent
   decides whether to proceed or escalate.
```

## 6. SARIF output shape and aggregation

### 6.1 SARIF as the canonical format

SARIF 2.1.0 is the deterministic-layer's output format because:

- It's machine-readable and standardised (OASIS).
- Every modern security analyzer produces it (Semgrep, ESLint, Bandit native; the rest via thin normalisation shims).
- It has a place for everything we need: results with locations, taxonomies (CWE, OWASP), tool driver provenance, free-form `properties`.

The CLI's output document wraps SARIF in a small envelope:

```json
{
  "schema_version": "1.0",
  "request": { "scope": "...", "diff_range": "...", "languages": [...] },
  "analyzers": {
    "semgrep": { "status": "ok", "duration_s": 12.4, "findings_count": 5 },
    "bandit":  { "status": "ok", "duration_s": 3.1, "findings_count": 2 },
    "gitleaks":{ "status": "ok", "duration_s": 1.4, "findings_count": 0 },
    "...":     { "...": "..." }
  },
  "sarif": { /* SARIF 2.1.0 with consolidated runs */ },
  "metrics": { "per_file": {...}, "per_class": {...}, "coupling": {...} },
  "ranked_hotspots": [
    { "file": "src/auth.py", "composite_score": 0.87, "factors": {...} },
    { "file": "src/api.py",  "composite_score": 0.64, "factors": {...} }
  ]
}
```

### 6.2 Dedup rule

Findings deduplicate by **(file, line ±tolerance, CWE)**.

- `line_tolerance` defaults to 3, configurable in `code-review.toml`.
- Two findings without a shared CWE never merge, even at the same line — they describe different things that happen to coincide.
- When merging, the highest severity from any source wins. `properties.sources` lists every contributing adapter. `properties.original_locations` lists every original line number for audit.
- The merge anchor is *CWE*, not free-form tags. Adapters that don't tag with CWE (e.g., dependency-cruiser's cycle detection) get a CWE-less identity that only merges with itself.

### 6.3 Severity mapping

Table-driven, in `code_review/severity.py`. Defaults:

| Input | Output (SDLC severity) |
|---|---|
| `level=error` ∨ `properties.severity in {critical}` | `critical` |
| `level=warning` ∧ `properties.severity in {high, important}` | `important` |
| `level=warning` (no severity property) | `minor` |
| `level=note` ∨ `properties.severity in {low, info, nit}` | `nit` |
| Contract violations (from Schemathesis) | `critical` (overrides above) |

Operator can override individual entries in `code-review.toml`:

```toml
[severity_overrides]
"semgrep:python.lang.security.audit.weak-crypto" = "important"
```

### 6.4 Hotspot scoring

Per-file composite score, weighted sum normalised to [0, 1]:

```
score(file) =
    w_critical  · count(findings, severity=critical)
  + w_important · count(findings, severity=important)
  + w_minor     · count(findings, severity=minor)
  + w_cc        · normalized_cyclomatic_complexity(file)
  + w_fan       · normalized(fan_in(file) + fan_out(file))
  + w_lcom      · normalized_inverse_cohesion(file)   # 1 - LCOM4
```

Weights default in `code-review.toml`:

```toml
[hotspot_weights]
critical = 5.0
important = 2.0
minor = 0.5
cc = 1.0
fan = 0.8
lcom = 0.6
```

Sub-agent uses the top N hotspots (default 10) to focus design-review attention and to pick refactor targets when filing fix tasks.

## 7. JSON Schemas and capability declaration

Three schemas, all in `.claude/skills/code-review/schemas/`:

- **`capabilities.json`** — declares what the skill can do. Read by the sub-agent on startup or every hour (whichever is shorter) to decide which analyzers to ask for. Contains review kinds, stack coverage, analyzer registry (id, kind, languages, rule_classes, taxonomies_tagged, default_timeout_s, scope_restriction), taxonomies (CWE, OWASP, SDLC severity).
- **`review-request.json`** — shape of CLI inputs (scope, diff, analyzers, output path).
- **`review-response.json`** — shape of the consolidated CLI output (§6.1).

Validation:

- The CLI validates its own inputs against `review-request.json` on startup.
- The CLI validates its own output against `review-response.json` before writing, in test/debug mode; in production mode this is a best-effort post-write check that logs but doesn't block.
- The sub-agent validates the CLI output it reads against `review-response.json` to catch protocol drift.

All schemas use JSON Schema draft 2020-12, validated by `jsonschema`.

**Offline validation guarantee.** The `jsonschema` library can fetch external metaschemas by URL (e.g. `https://json-schema.org/draft/2020-12/schema`); under the Claude Code sandbox, those fetches would fail. The CLI explicitly pre-loads every metaschema into a `referencing.Registry` (via `jsonschema_specifications.REGISTRY`) and constructs validators with that registry, so no network call is ever attempted. A test in `test_sandbox_compatibility.py` asserts this by patching the network stack to fail any attempted connection during a validation pass.

## 8. Sub-agent integration

> **Entirely superseded by ADR-0010 (2026-05-28).** The whole section described a `reviewer` sub-agent that this skill would install via `setup.sh` and that would (a) read a `review_scope` config, (b) invoke the CLI, (c) perform LLM design review in the same turn, (d) file fix tasks. None of this lives in `code-review` any more. The bundled `agents/reviewer.md` and `setup.sh`'s reviewer-install step were removed in s5 Phase 3. The design-review responsibilities move to the `intent-review` sibling project; cross-skill dedup is a future consumer LLM's job by judgment, not a built-in. The text below is retained as historical record.

### 8.1 The reviewer sub-agent's invocation pattern

The `code-review` skill updates the existing `.claude/agents/reviewer.md` to add scope-aware behaviour. The updated sub-agent reads the SDLC skill's `review_scope` config on every dispatch and branches accordingly:

**At `lite` scope:** the sub-agent skips the CLI entirely and performs LLM-only review — reading the diff, surfacing issues from its own reasoning, and routing findings per the SDLC taxonomy. This is behaviourally identical to the current SDLC reviewer. No deterministic tools run. No subprocess is spawned.

**At `standard` and `full` scope:** the sub-agent's prompt instructs it to:

1. Read the current task's spec, plan, and diff.
2. Read the `review_scope` config from the SDLC skill's project-level config.
3. Run `python -m code_review.cli --capabilities` via Bash. Parse the JSON. If any policy-required analyzer for the active scope (e.g., gitleaks at `standard`, Schemathesis at `full`) is `unavailable`, escalate via the Autonomy gate.
4. Run `python -m code_review.cli --review-scope <scope> --scope <timing> --diff <range> --output .claude/skills/code-review/runs/<id>.json` via Bash. Wait for completion. (The `--review-scope` flag selects the analyzer set; `--scope` selects per-task vs story-level timing. Both are required.)
5. Read `.claude/skills/code-review/runs/<id>.json`. Inspect `analyzers.<name>.status` — if any are `error`, surface the failure and stop (do not silently mark the task done).
6. **Perform LLM design review** in this same turn:
   - Read the diff.
   - Read the consolidated SARIF.
   - Surface only issues the rule-based layer can't catch: domain-naming mismatches, architectural drift, abstraction quality, missing tests for edge cases the spec implies, intent vs spec misalignment.
   - Explicitly do not duplicate deterministic findings — the sub-agent's prompt enforces this with a "for each candidate finding, check whether it falls within ±3 lines of a deterministic finding tagged with the same CWE; if so, drop it" rule.
   - Emit design findings as a small SARIF run with `tool.driver.name = "llm-design"`, `ruleId` prefixed `llm-design.`, and `properties.sdlc_severity` set directly per the SDLC taxonomy.
7. Merge design findings into the consolidated review (in memory; no rewrite of `runs/<id>.json` needed).
8. Route findings per the SDLC taxonomy (assumed stable; see §17):
   - **Critical, Important** → file `-fix<N>-<slug>` task in `/sdlc/work/active/`, with frontmatter:
     ```yaml
     ---
     id: <parent-task-id>-fix<N>-<slug>
     kind: task
     parent: <parent-story-id>
     sources: [".claude/skills/code-review/runs/<id>.json"]
     created: <today>
     updated: <today>
     ---
     ```
     Insert at front of remaining task queue per the SDLC's auto-progress rules.
   - **Minor** → append one entry per finding to the parent task's `notes:` field, formatted as `<file>:<line> — <message> (source: <adapter>)`.
   - **Nit** → drop. Log the count for audit only.
9. If filing fix tasks would cross the rule #25 round-2 boundary, halt and escalate to the operator via the Autonomy gate. Don't silently file round-3 fix tasks.
10. Write a summary report (one paragraph + bullet counts by severity) to the operator-visible turn output.

### 8.2 The scope-to-analyzer mapping

The CLI resolves `--review-scope` to an analyzer set using a static mapping in `capabilities.json`:

| Scope | Analyzers included |
|---|---|
| `lite` | *(CLI not invoked; LLM-only)* |
| `standard` | Semgrep, Bandit, gitleaks, Trivy, Radon, vulture, jscpd, knip, ESLint+sonarjs |
| `full` | Everything in `standard` + pydeps, dependency-cruiser, cohesion, Schemathesis |

The Schemathesis contract-testing adapter only fires at story-level timing regardless of scope — the CLI enforces this via the existing scope-restriction mechanism from §4.

The operator can override the mapping per-project via `code-review.toml`'s `[scope_overrides]` section, but the three-scope interface is the primary design and the overrides are documented as an advanced escape hatch, not promoted in the SKILL.md quick-start.

### 8.3 The `review_scope` config key

The SDLC skill exposes a project-level config key, `review_scope`, with default value `lite`. When the `code-review` skill is installed and the operator wants richer reviews, they change one line:

```toml
# in the SDLC skill's project-level config
review_scope = "standard"   # or "full"
```

Switching scopes takes effect on the next Review dispatch. No restart, no reinstall, no other artefacts touched. Reverting to `lite` restores the LLM-only behaviour.

### 8.3 Why the LLM step stays inside the sub-agent's turn

This is the architectural commitment that lets us use the interactive subscription pool. Three properties have to hold:

- **No `claude -p` invocation anywhere in the flow.** Verified by a test that fails if the string `claude -p` or `--print` appears in any shell command executed during a review (excluding documentation).
- **No `ANTHROPIC_API_KEY` consulted by the reviewer skill.** Verified by a test that runs the CLI with `ANTHROPIC_API_KEY=should-not-be-used` and asserts the value never appears in any subprocess environment.
- **No Anthropic SDK import in `code_review/`.** Verified by `mypy` + a static check (`grep -r "import anthropic\|from anthropic" code_review/` returns nothing).

All three are CI assertions, not just discipline. The s5 story has them as acceptance criteria.

### 8.4 What happens if the turn budget is too small

Story-level diffs on large stories may push the sub-agent toward context-window pressure. The sub-agent's prompt includes an explicit check: if after reading the consolidated SARIF the sub-agent estimates that adding the full diff to its working context would exceed safe headroom, it emits a "context budget pressure" diagnostic and escalates to the operator suggesting the design-review be re-dispatched as its own sub-agent. It does **not** silently truncate the diff and continue. The s5 acceptance criteria mandate this explicitly.

## 9. Concurrency, timeouts, and process management

### 9.1 Concurrency

- One `asyncio.TaskGroup` in `code_review/cli.py` for the analyzer fan-out.
- Each adapter is one task in the group.
- The group implicitly waits for all tasks before exiting; exceptions inside the group don't propagate to other tasks (adapters catch their own).
- No semaphore. Analyzer count is bounded (~12), each is one subprocess, and we'd rather over-saturate IO for ~30 seconds than micromanage. If this turns out to thrash on resource-constrained machines, a `BoundedSemaphore` is one line.

### 9.2 Timeouts

- Default per-adapter timeout from `capabilities.json` (e.g., Bandit 60s, Trivy 180s, Schemathesis 600s).
- Override via `code-review.toml`'s `[timeouts]` table.
- Implementation: `asyncio.wait_for(adapter.run(request), timeout=N)` inside each task.
- On timeout: the `wait_for` raises `TimeoutError` *inside the adapter*; the adapter's subprocess handler sends `SIGTERM` to the process group, waits 2s, then `SIGKILL`. The adapter returns `AnalyzerOutput(status="timeout", ...)` rather than propagating the exception.

### 9.3 Subprocess invocation

- **Always `asyncio.create_subprocess_exec`**, never `subprocess.run` or `os.system`. Blocking the event loop would silently serialise the fan-out.
- Subprocesses spawned with `start_new_session=True` so we get a process group leader and can clean up children on timeout.
- stdin closed; stdout/stderr captured to bytes; decoded with `errors="replace"` to handle tool output that's occasionally not valid UTF-8.
- Env: starts from a copy of `os.environ`, with explicit redactions for auth-related vars before any adapter runs (see §11).

### 9.4 Diff scoping

- The CLI calls `git diff --name-only <range>` once at the start to get the touched-file list.
- Per-adapter handling depends on tool support:
  - Adapters that accept a path or file list (`semgrep`, `eslint`, `bandit`, `radon`): pass touched paths directly.
  - Adapters that only run on a whole tree (`dep-cruiser`, `pydeps`): run on the whole tree, then post-filter SARIF results to only those whose `physicalLocation.artifactLocation.uri` is in the touched-file set.
- Whole-tree adapters are noted in `capabilities.json` so the operator can see why they're slower at story-level scope.

## 10. Configuration and uv-based build

### 10.1 `pyproject.toml`

uv-managed. All tool versions **pinned exactly** as agreed during tool-stack review:

```toml
[project]
name = "code-review"
version = "0.1.0"
description = "Deterministic analyzer layer for the SDLC reviewer sub-agent"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "typer == 0.18.0",
    "jsonschema == 4.26.0",
    "bandit == 1.7.10",        # adapter-internal
    "radon == 6.0.1",
    "vulture == 2.13",
    "pydeps == 1.12.20",
    "cohesion == 1.1.0",
    "schemathesis == 4.0.10",
    # Subprocess-only tools (semgrep, gitleaks, trivy, eslint, dep-cruiser,
    # jscpd, knip, pact) are NOT Python dependencies. They are runtime
    # prerequisites listed in README + capabilities.json runtime check.
]

[dependency-groups]
dev = [
    "pytest == 8.3.4",
    "pytest-asyncio == 0.25.0",
    "mypy == 1.13.0",
    "ruff == 0.15.14",
]

[project.scripts]
code-review = "code_review.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
package = true

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 10.2 Why exact pins

The two mitigations agreed during tool-stack review:

- **Tool versions are deliberately governed** per **ADR-0003** (original exact-pin policy) and **ADR-0013** (2026-05-29 partial supersede). Post-ADR-0013 the split is: runtime deps in `[project.dependencies]` carry lower-bound `>=` specifiers anchored at the currently-locked minor (consumer-resolution friendly); `uv.lock` continues to pin exact patches (developer reproducibility, "deliberate, reviewed bump" governance attaches here); dev deps in `[dependency-groups] dev` stay exact-pinned. The justification — protecting against upstream governance churn like the Astral/OpenAI situation — is unchanged; only the *layer* at which exactness is enforced moves for runtime deps. See `stack-pins.md` §"Pinning policy" for the canonical phrasing.
- **Pip-install fallback works** — `pyproject.toml` follows PEP 621 conventions. Anyone can `pip install -e .` (with Python ≥3.11) and have a working environment. uv is preferred but not required.

Two operational consequences:

- We **invoke `ruff` only via CLI**, never as a library import. If a fork or alternative is needed later, only the CI scripts change.
- We **never depend on uv-specific `pyproject.toml` features**. `uv.lock` exists alongside but is uv-specific; everything in `pyproject.toml` is portable.

### 10.3 Developer workflow

```
# First-time setup (and after dependency changes)
./scripts/setup.sh
# This script runs, in order:
#   uv sync --frozen                # Python deps from uv.lock
#   npm ci                          # Node deps from package-lock.json
#                                   # populates ./node_modules
#   uv run python scripts/prefetch_caches.py
#                                   # downloads Trivy DB, Semgrep rules
#                                   # into ./cache/ for offline use
# setup.sh must be run OUTSIDE the sandbox the first time, because
# it needs network to populate caches that the sandboxed runtime then
# reads offline. Re-running it after the caches exist is idempotent.

# Run the CLI
uv run python -m code_review.cli --capabilities

# Run tests (most tests; --requires-docker skipped)
uv run pytest

# Run all tests including Docker-fixture ones (run outside sandbox)
uv run pytest --run-docker

# Run static checks
uv run ruff check .
uv run ruff format --check .
uv run mypy code_review/

# Add a dependency (deliberate, reviewed)
uv add some-package == X.Y.Z
npm install --save-exact some-js-package@X.Y.Z
```

### 10.4 CI

CI workflow (whatever runner; the architecture is platform-agnostic):

1. `uv sync --frozen` — installs exactly what's in `uv.lock`, no resolution.
2. `uv run ruff check . && uv run ruff format --check .`
3. `uv run mypy code_review/`
4. `uv run pytest`
5. **Subscription-pool assertion** (s5 story): grep the test output for any `claude -p` invocation, any `ANTHROPIC_API_KEY` env reference, any `anthropic` package import — fail CI if found.
6. **No-SDLC-diff assertion** (s5 story): if `.claude/agents/reviewer.md` is in the diff, assert `/sdlc/SDLC.md` is not.

## 11. Security and license posture

### 11.1 License floor

- Skill code: **MIT**.
- Python dependencies: **MIT / Apache-2.0 / BSD only**. No LGPL, no GPL, no AGPL in import paths.
- Subprocess-only tools may be GPL/LGPL (e.g., Semgrep is LGPL-2.1, gitleaks is MIT, Trivy is Apache-2.0). LGPL is fine when invoked as a separate process. **No AGPL anywhere**, even via subprocess (confirmed during research — TruffleHog was rejected for this reason in favour of gitleaks).
- License audit is part of CI: a `uv run python scripts/license_audit.py` step verifies that every direct + transitive dependency's license falls in the allow-list. The script and allow-list live in `scripts/`.

### 11.2 Secrets handling

The CLI must never leak credentials. Concrete rules:

- **Auth tokens for Schemathesis / Pact** come from environment variables named in `code-review.toml` (`auth.token_env = "FIXTURE_API_TOKEN"`). The CLI reads the named env var, passes it to the adapter, and **redacts it from subprocess `argv` and stdout/stderr capture**.
- **No tokens in CLI args.** Adapters that take auth send it via header injection or env var to the underlying tool, not via `--auth <token>`.
- **Per-finding raw-output debug files** at `.claude/skills/code-review/cache/raw/<adapter>.<ext>` are filtered through a secrets-redaction regex pass before being referenced from the consolidated output.
- An automated test plants a known token in the env, runs a Schemathesis-using fixture, and grep-asserts the token never appears in `cache/raw/`, in the consolidated output, or in CLI stderr/stdout.
- **Defense-in-depth: recommend `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`** in the skill's README. Claude Code honours this env var to strip Anthropic and cloud-provider credentials from subprocesses; the skill works without it, but the recommendation gives the operator a second layer of protection against any future code that might accidentally read `ANTHROPIC_API_KEY` from the environment.

### 11.3 Subprocess argument injection

- **Never construct subprocess argv from concatenated strings.** `asyncio.create_subprocess_exec` takes a list of args, each passed to `execve` directly — no shell, no quoting.
- **Validate diff ranges as `[a-fA-F0-9./~^_-]+` before passing to git**. A malformed range (e.g., one containing `;` or `$()`) is rejected with a clear error.
- **Adapter configs from `code-review.toml` are validated against a schema before being passed to adapters.** No raw user TOML reaches an adapter.

### 11.4 Filesystem access

- The CLI writes only to `--output` (consolidated JSON) and to `.claude/skills/code-review/cache/raw/<adapter>.<ext>` (debug raw output). Both paths sit inside the project's CWD, which is the sandbox's default writable region.
- Atomic writes: `.tmp` + `os.rename`. No partial files visible.
- The CLI never writes to `/sdlc/`. That's the sub-agent's responsibility, governed by the SDLC's file conventions.
- The CLI may read from anywhere under the repo root (analyzers need source access) but never follows symlinks outside the repo.

## 12. Testing strategy

Three test layers, all running under `uv run pytest`:

### 12.1 Unit tests

- `test_contracts.py` — Protocol surface, dataclass invariants.
- `test_severity.py` — exhaustive table-driven mapping test.
- `test_aggregator.py` — dedup correctness with golden-file SARIF inputs.
- `test_cli.py` — argument parsing, schema validation of input, exit codes.

### 12.2 Adapter integration tests

One test module per adapter at `tests/test_adapters/test_<name>.py`. Each:

1. Runs the adapter against a fixture in `tests/fixtures/` with at least one known finding.
2. Asserts the SARIF validates against `schemas/sarif-2.1.0.json`.
3. Asserts the known finding appears with the expected `ruleId` and location.
4. Asserts the adapter's status, duration, and metric output (where applicable).

Tests that require external services (Pact broker, Schemathesis target API) use `docker-compose` fixtures invoked by `conftest.py`. These tests are marked `@pytest.mark.requires_docker` and skipped if Docker isn't available. Docker is incompatible with the Claude Code sandbox by Anthropic's own documentation — see §16.7 — so these tests run outside `/sandbox`, either in CI without sandboxing or on the developer's host. They never assume bubblewrap-in-container will work; if you need to run them inside a containerised CI environment, `sandbox.enableWeakerNestedSandbox` must be enabled at the outer layer.

### 12.3 End-to-end tests

- `test_subagent_integration.py` — invokes the CLI in a subprocess, exactly as the sub-agent would. Uses a fixture repo with planted findings across all four severities. Asserts the consolidated output shape and the per-finding routing decisions a downstream sub-agent would make.
- `test_subscription_pool_assertion.py` — verifies the no-`claude -p`, no-`ANTHROPIC_API_KEY`, no-`anthropic`-import properties. Implementation: subprocess-level monitoring during a full review run, plus static grep checks. This test runs *inside* a `/sandbox`-enabled session (CI script enables sandboxing before invoking pytest for this file) so it exercises the same OS-level boundary the production sub-agent would see — not a softer dev-machine environment.
- `test_sandbox_compatibility.py` — the explicit sandbox-compatibility test suite (see §16.9). Asserts: no writes outside CWD, no network calls outside the documented allowlist, no shell metacharacters in subprocess argv, no `/tmp` references in production code paths (static grep), no symlink-following outside the repo, and that all bundled metaschemas resolve without network.
- **FakeAnalyzer harness** — used by both unit and end-to-end tests where real subprocesses would be slow or unstable. The harness implements the Protocol and returns canned SARIF; it flows through the same CLI code path real adapters use. This is the seam that proves the architecture's main bet (everything goes through one Protocol) is real.

### 12.4 Coverage discipline

- Tests are required for every adapter listed in `capabilities.json`'s `stack_coverage`. This is enforced by a meta-test that walks `capabilities.json` and asserts a matching fixture exists. Prevents drift between declared coverage and actual coverage.

## 13. Observability

Minimal, by design. No OpenTelemetry across processes; no spans, no distributed tracing — the sub-agent and CLI live in one process tree.

What we keep:

- **Stdlib `logging` with `logging.JSONFormatter`.** Each adapter logs start, end, status, duration as a single JSON line to stderr.
- **`.claude/skills/code-review/cache/raw/<adapter>.<ext>`** for raw adapter output, post-secrets-redaction. Useful when debugging why an adapter produced a finding (or didn't). The path is gitignored and inside CWD per sandbox compatibility rules.
- **CLI stdout summary line** — one line per invocation, parseable: `analyzers: 8 | findings: 14 | duration: 41.2s | exit: 0`.
- **No persistent log file from the CLI itself.** The operator's Claude Code session already records every Bash invocation and its output; we don't double-log.
- **No cost tracking.** The LLM step runs inside the operator's interactive session, billed against the subscription pool — there's nothing to track at the skill layer. If the operator wants to see session-level cost, they get it from the Claude Code session's existing reporting.

## 14. Failure modes and degradation

A short matrix of how the system behaves when things go wrong:

| Failure | Behaviour |
|---|---|
| One adapter's binary missing | `--capabilities` reports it as `unavailable`. Sub-agent escalates before submitting a review *if* the missing analyzer is policy-required; otherwise proceeds with the available set. |
| One adapter crashes mid-run | `status="error"`, `error` field populated, CLI exits non-zero, sub-agent escalates. Other adapters' results preserved. |
| One adapter times out | `status="timeout"`, partial findings (if any) preserved, CLI exits 0 (timeout is expected; error is not). |
| CLI itself crashes (bug) | Subprocess exits non-zero with traceback on stderr. Sub-agent escalates per Autonomy gate — does not close the task. |
| Sub-agent's LLM design step fails (rare; e.g., context budget exhausted) | Sub-agent emits the deterministic findings only, with a clear note that design review was skipped, and escalates to the operator. |
| Aggregator produces invalid output | Best-effort post-write schema check logs a warning; downstream sub-agent's input validation catches it and escalates. |
| Two adapters disagree on severity for the same finding | Highest severity wins per §6.2; both adapters listed in `properties.sources`. |
| `code-review.toml` is malformed | CLI exits non-zero with a clear pointer to the offending TOML entry. No best-effort fallback to defaults — the operator should see the problem. |

The general posture: **fail visibly, never silently**. The SDLC's autonomy rules (line 14) mandate escalation over guessing, and this architecture honours that throughout.

## 15. What changes if the assumptions go wrong

Three big bets in this architecture. If any one fails during validation, here's what we'd revisit:

- **If the deterministic+LLM layering doesn't beat LLM-only** (finding overlap < 30% on validation diffs) — the whole epic loses its rationale. We'd remove the deterministic CLI and revert to the current LLM-only sub-agent. The architecture is small enough that this isn't a sunk cost; the adapters are independent units of work.
- **If the sub-agent's turn budget can't host both deterministic interpretation and design review** on routine story-level diffs — split into two sub-agents: one runs the CLI and consolidates, the other gets dispatched with the consolidated SARIF and does design review only. This is a structural change but doesn't require any analyzer rewrite.
- **If SARIF is the wrong canonical format** — most likely, this would show up as the LLM design step struggling to convert SARIF findings back into useful prose. The fix is to add a secondary "human-readable findings summary" alongside the SARIF in the consolidated output, not to replace SARIF (whose value as machine-readable metadata stands regardless).

The architecture's load-bearing decision is **the Analyzer Protocol**. If that's right, every other choice is replaceable.

## 16. Sandbox compatibility

The Claude Code sandbox (`/sandbox`) imposes OS-level filesystem and network restrictions on every Bash command and its child processes. Per Anthropic's documentation, sub-agents "run in the same process as the parent session and use the same sandbox configuration" — meaning every `python -m code_review.cli` call, and every analyzer subprocess underneath it, runs under the operator's sandbox. The architecture below is designed to work under the default sandbox configuration with the narrowest possible widening; this section enumerates exactly what the sandbox enforces, what the skill needs from it, and the rationale for every widening.

### 16.1 What the sandbox enforces by default

- **Writes:** allowed only to the current working directory (CWD) and its subtree. Writes elsewhere (`/tmp`, `~/`, `/usr/`, etc.) are blocked at the OS level. macOS uses Seatbelt; Linux and WSL2 use bubblewrap.
- **Reads:** broad by default — most of the filesystem is readable, including credential files. The operator may further restrict via `denyRead`.
- **Network:** denied by default. The first time a Bash command needs a new domain, Claude Code prompts the operator for approval; pre-approving domains via `allowedDomains` skips the prompt.
- **Environment variables:** inherited from the parent process by default. `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` can strip Anthropic and cloud-provider credentials.
- **Settings files are protected:** the sandbox automatically denies write access to `.claude/settings.json` and `~/.claude/settings.json`, so a sandboxed command cannot widen its own policy.

### 16.2 Sandbox-driven architectural decisions

These are decisions made specifically to comply with the sandbox; they appear elsewhere in the document but are listed here as one place to audit:

| Decision | Rationale |
|---|---|
| Output files in `.claude/skills/code-review/runs/`, not `/tmp` | CWD writes are allowed by default; `/tmp` is not. |
| Per-adapter caches in `.claude/skills/code-review/cache/`, not `~/.cache` | Same reason. |
| Node tooling vendored to `node_modules/` (committed `package-lock.json`, invoked as `node ./node_modules/.bin/<tool>`) | `npm install` / `npx` fetch from the registry, which is blocked by default network policy. |
| Trivy DB and Semgrep rule packs pre-fetched at setup time, used in offline mode at runtime | The CVE feed and rule-pack registry are outside the default `allowedDomains`. Pre-fetching avoids runtime network. |
| Schemas pre-loaded into a `referencing.Registry` | Avoids any runtime metaschema fetch. |
| `paths.py` resolves all skill-relative paths from a single anchor | Adapters never assume a particular CWD layout; tests can inject a temporary skill root. |
| Recommend `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` | Defense-in-depth: no LLM credentials in subprocess env, even if a future bug tried to use them. |

### 16.3 Per-adapter sandbox accommodations

Each analyzer has been audited for write locations and network needs. The table below records what each adapter does by default and what override the skill applies:

| Adapter | Default write location | Default network | Skill override |
|---|---|---|---|
| Semgrep | `~/.semgrep_logs/` and (registry mode) `~/.semgrep/` cache | Yes, for rule packs | `--metrics off` + `SEMGREP_USER_DATA_FOLDER=./cache/semgrep`; use local rules from `./cache/semgrep-rules/` pre-fetched at setup |
| Bandit | None | None | None needed |
| gitleaks | None | None | None needed |
| Trivy | `~/.cache/trivy/` for DB | Yes, for DB updates | `--cache-dir ./cache/trivy-db --skip-db-update --offline-scan`; DB pre-fetched at setup |
| Radon | None | None | None needed |
| vulture | None | None | None needed |
| pydeps | None | None | None needed |
| cohesion | None | None | None needed |
| jscpd | None (writes to `./.jscpd/` if `--output`) | None | Default config keeps output inline |
| ESLint | `./.eslintcache` if enabled (inside CWD) | None for local rules; yes for plugin auto-install | Pin all plugins in `package.json`; never use auto-install |
| dependency-cruiser | None | Some configs check npm registry | Use offline-only config; the JSON output adapter doesn't need network |
| knip | None | None | None needed |
| Schemathesis | Hypothesis cache redirected to `$TMPDIR` via `HYPOTHESIS_STORAGE_DIRECTORY` (per s4 / s3 tempfile pattern) | **Yes — hits the target API** | Operator must add the target API host to `sandbox.allowedDomains`. Story-level only. |

All adapters that touch the filesystem are tested under sandbox in `test_sandbox_compatibility.py` to confirm they respect these overrides.

### 16.4 Network policy

The skill expects one of two postures from the operator's sandbox network configuration:

**Per-task review:** zero network access required. All adapters run offline; the CLI doesn't reach out. The operator does not need to widen `allowedDomains` at all.

**Story-level review with contract testing:** the operator widens `allowedDomains` with exactly the targets named in their `code-review.toml`:

```toml
[contract_testing]
schemathesis_target = "http://localhost:8080"
pact_broker = "http://localhost:9292"
```

The skill's README provides a copy-paste `settings.json` snippet:

```json
{
  "sandbox": {
    "allowedDomains": [
      "localhost"
    ]
  }
}
```

Production targets (real broker URL, real API host) replace `localhost` as appropriate. The skill never asks for, and never benefits from, a wildcard or broad allow such as `*`, `github.com`, or `npmjs.com`.

### 16.5 Filesystem widening — what the skill does NOT need

These are deliberate non-requirements. The skill works without any of:

- `sandbox.filesystem.allowWrite` extensions — all writes stay in CWD.
- `excludedCommands` entries — every analyzer runs inside the sandbox.
- `allowUnsandboxedCommands: true` — the escape hatch is not needed.
- `allowUnixSockets` — no analyzer needs Unix-socket access.
- Read widening — the default broad-read policy is sufficient.

If a future change needs any of these, that change must come with an architectural review and an updated entry in §16.2.

### 16.6 Environment scrubbing

The CLI's subprocess base class (`adapters/base.py`) starts from a copy of `os.environ` and applies explicit redactions before invoking any analyzer:

```python
SCRUBBED = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "OPENAI_API_KEY",
    # plus operator-configured extras from code-review.toml [env.scrub]
)
```

The scrubbing happens unconditionally in the CLI, *whether or not* the operator has set `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`. The Anthropic-provided env scrub is the recommended outer defence; this list is the inner one and includes a broader set of credential vars.

### 16.7 Docker incompatibility

Per Anthropic's docs, `docker` commands fail inside the sandbox and must be added to `excludedCommands` to run unsandboxed. We deliberately do not depend on Docker at runtime:

- **The Pact broker and Schemathesis fixture targets are external services**, not Docker containers spawned by the skill. The operator runs them however they like (Docker Compose for tests, real deployment for production); the skill doesn't care.
- **Test fixtures** that need Docker (Pact broker fixture, Schemathesis target fixture) are marked `@pytest.mark.requires_docker` and **run outside the sandbox** — either on the developer host without `/sandbox` enabled, or in a CI environment with `sandbox.enableWeakerNestedSandbox: true` at the outer layer.

If the operator's CI runs Claude Code inside a container, they must enable `enableWeakerNestedSandbox`, which Anthropic flags as a security weakening — the responsibility for that trade-off sits with the CI operator, not the skill.

### 16.8 Sandbox bypass risk and mitigation

Anthropic's docs note that "when a command fails because of sandbox restrictions, Claude analyzes the failure and may retry the command with the `dangerouslyDisableSandbox` parameter." A March 2026 incident showed Claude Code disabling its own sandbox to complete a task. The reviewer sub-agent must not do this. Three mitigations:

- **The sub-agent's prompt explicitly forbids retrying with `dangerouslyDisableSandbox`.** If a Bash command fails under sandbox, the sub-agent surfaces the failure to the operator and escalates via the Autonomy gate — it does not retry unsandboxed.
- **The CLI's exit codes distinguish sandbox-related failures from analyzer failures** so the sub-agent can recognise the difference. A command that exits with the bubblewrap/Seatbelt "operation not permitted" pattern is treated as a configuration problem, not an analyzer bug.
- **The operator's recommended `settings.json` includes `"allowUnsandboxedCommands": false`** — strict-sandbox mode — which makes the `dangerouslyDisableSandbox` parameter inert at the Claude Code layer regardless of what the sub-agent might try. The skill's README documents this as the recommended posture.

### 16.9 Sandbox-compatibility test

`test_sandbox_compatibility.py` is a dedicated test module that exercises these properties:

- **No writes outside CWD:** runs a full review, then `find / -newer <test-start> -type f 2>/dev/null` and asserts the result set is contained within CWD.
- **No network outside the allowlist:** wraps the test in a network sniffer (`strace -e trace=connect` on Linux; `dtruss` on macOS) and asserts every outbound connection target matches the documented allowlist.
- **No `/tmp` references in code:** `grep -r '"/tmp/' code_review/` returns empty (excluding comments).
- **No shell metacharacters reach subprocess argv:** fuzz-test the `diff_range` validator with strings containing `;`, `$()`, `&&`, `|`, backticks; all rejected.
- **No symlink-following outside the repo:** plant a symlink in the fixture pointing outside the repo; assert the CLI does not read through it.
- **Bundled metaschemas resolve without network:** patch `socket.socket` to raise on any connect attempt during a validation pass; assert validation still succeeds.
- **Sandbox-bypass refusal:** mock a Bash command failure with the bubblewrap "operation not permitted" signature; assert the sub-agent fixture escalates rather than retrying with `dangerouslyDisableSandbox`.

This test is part of CI and is a release gate: the skill does not ship if any assertion fails.

### 16.10 Worked example — what the operator's settings.json looks like

For an operator running this skill, the recommended `.claude/settings.json` (project-scope) is:

```json
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "filesystem": {},
    "allowedDomains": []
  }
}
```

All five sandbox keys take their strictest sensible values. The skill works under this configuration for per-task reviews without any further widening.

For story-level reviews that include Schemathesis or Pact, the operator adds the specific target hosts to `allowedDomains` — and *only* those hosts:

```json
{
  "sandbox": {
    "allowedDomains": ["localhost", "pact-broker.internal"]
  }
}
```

That is the entire surface of operator-side sandbox configuration this architecture requires.

## 17. SDLC contract surface

The `code-review` skill depends on the SDLC skill for several conventions but does not enforce a version check (see hypothesis 5 in the epic). This section enumerates exactly what the `code-review` skill assumes the SDLC skill provides, so that future changes to either side are at least visible as a contract surface. Treat this list as the upstream interface: if any item changes, the `reviewer` sub-agent will need an update.

### 17.1 Severity taxonomy

Four levels, in decreasing order of impact: **Critical**, **Important**, **Minor**, **Nit**. The `code-review` aggregator (§6) maps every consolidated finding to one of these four values, written into `properties.sdlc_severity` on the SARIF result.

The the `reviewer` sub-agent routes findings by severity as defined in the SDLC skill's Review verb behaviour:

- Critical and Important → file fix tasks
- Minor → append to parent task notes
- Nit → drop

If the SDLC skill adds a fifth severity level, removes Minor, or changes the routing rule, the `reviewer` sub-agent breaks at the routing step. The fix is a one-table edit to `code_review/severity.py` plus a corresponding update to the sub-agent prompt.

### 17.2 Fix-task naming convention

Fix tasks follow the pattern `<parent-task-id>-fix<N>-<slug>` where `<N>` is the remediation round (1 for direct fix tasks, 2 for fixes of fixes). The the `reviewer` sub-agent writes files matching this pattern into `/sdlc/work/active/`.

If the SDLC skill changes the naming convention — different separator, different round numbering, additional path components — the `reviewer` sub-agent will write tasks the SDLC skill no longer recognises. The fix is an update to the sub-agent prompt; the underlying analyzer code is unaffected.

### 17.3 Rule #25: 2-round remediation bound

The SDLC's auto-remediation loop stops after two rounds of fix tasks per parent task. Round 3 is forbidden; the sub-agent must escalate via the Autonomy gate instead. The the `reviewer` sub-agent honours this by tracking the remediation depth in its own logic and refusing to file round-3 fix tasks.

If the SDLC skill changes the round bound, the `reviewer` sub-agent's constant needs updating. If the SDLC skill removes the bound entirely, the `reviewer` sub-agent continues to enforce its own 2-round limit (defensive default).

### 17.4 Autonomy gate

The SDLC skill provides an escalation interface — the `reviewer` sub-agent calls it when:

- A policy-required analyzer is unavailable (§8.1 step 2).
- The CLI exits non-zero (§14).
- Rule #25 round-3 would be triggered (§17.3).
- Context budget pressure is detected during LLM design review (§8.4).
- A Bash command fails with a sandbox-related error (§16.8).

The contract: the SDLC skill provides a callable mechanism (currently a documented prompt pattern, not a literal API) for the sub-agent to surface a decision to the operator with options to iterate, accept-as-debt, or rework. the `reviewer` sub-agent's prompt invokes this mechanism for the cases above.

If the SDLC skill changes the escalation interface, the sub-agent prompt needs updating. The analyzer code is unaffected.

### 17.5 `review_scope` config key — *superseded by ADR-0011 (2026-05-28)*

The `code-review` skill no longer reads any SDLC project-level config key. Selection is driven by the CLI's `--review` / `--depth` flags directly. The text below is retained for historical context.


The SDLC skill is assumed to expose a project-level config key named `review_scope` whose value controls the depth of review. Three valid values: `lite` (default; LLM-only), `standard`, `full`. The `reviewer` sub-agent reads this value on every dispatch and branches accordingly.

This is the *one* mechanism-level assumption the `code-review` skill makes about the SDLC skill's internal configuration. If the SDLC skill uses a different config key, or stores config in a different location, the `code-review` skill's SKILL.md and the sub-agent prompt need adjustment.

### 17.6 Project-level config location — *superseded by ADR-0011 (2026-05-28)*

Not applicable — the skill no longer reads SDLC config. Per-skill operator-tunable settings live in `code-review.toml` (read from the skill directory; CWD-resolution deferred per ADR-0007). The text below is retained for historical context.


The `code-review` skill's documentation tells operators which file holds the `review_scope` setting (e.g., the SDLC skill's project-level config — exact path is whatever the SDLC skill mandates). The `code-review` skill's CLI does not read this file itself; the sub-agent reads it and passes the value to the CLI via `--review-scope`.

If the SDLC skill changes the config location, the `code-review` skill's README and `SKILL.md` need updating. The analyzer code is unaffected.

### 17.7 SDLC artefact directories

The the `reviewer` sub-agent writes fix-task files into `/sdlc/work/active/`. It reads (but does not write) `/sdlc/work/done/`, `/sdlc/STATE.md`, and other SDLC-managed files as needed for context.

If the SDLC skill changes these paths — moves `work/active` to `work/in-progress`, adds a per-epic subdirectory, etc. — the sub-agent prompt needs updating.

### 17.8 What stays stable

Conversely, here is what the `code-review` skill does *not* depend on, even though it could:

- Specific SDLC.md text. The sub-agent prompt doesn't quote SDLC.md; it encodes the conventions directly.
- Specific line numbers in SDLC.md (e.g., "severity taxonomy at lines 166-169"). Those references appear in this architecture document for cross-reference but are not load-bearing — the conventions are duplicated in the sub-agent prompt itself.
- The SDLC skill's internal implementation of the `lite` scope path. At `lite` scope, the `reviewer` sub-agent does LLM-only review without invoking the `code-review` CLI. The CLI code does not need to know how `lite` works.

### 17.9 Update discipline

When the SDLC skill changes any item in §17.1–17.7, the operator (or whoever maintains the `code-review` skill) is expected to:

1. Read the SDLC skill's changelog or release notes.
2. Audit this section against the new SDLC behaviour.
3. Update the affected `code-review` code (sub-agent prompt, severity table, or both) and ship a new version.

There is no automation for this discipline. The architecture's bet (hypothesis 5) is that the SDLC's contract surface changes infrequently enough that manual cross-checking is acceptable.
