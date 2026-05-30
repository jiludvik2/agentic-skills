---
id: adr-0020-thin-invocation-runner
kind: decision
project: code-review
status: accepted
parent: epic-analyzer-thin-runner
sources: [post-coverage-eval-findings.md, vendor-js-semgrep-rules.md, g5-maintainability-oracle-repos.md, g8-js-complexity-cohesion-absent.md]
created: 2026-05-30
updated: 2026-05-30
tags: [architecture, facade, runner, sarif, simplification, supersedes-0006, amends-0010]
---

# ADR-0020: Replace the output-normalizing facade with a thin invocation runner

## Status

Accepted 2026-05-30 (operator-directed, this session). **Supersedes ADR-0006**
(SARIF as canonical format). **Amends ADR-0010**'s shared-format invariant (see below).
Retains ADR-0019 (unavailable-vs-error) and ADR-0011 (review-selection scheme).

## Context

The deterministic analyzer layer wraps ~13 external scanners. Per ADR-0006, every
tool's heterogeneous native output is **normalised into a single canonical SARIF
2.1.0 document** (+ `sdlc_severity`, cross-tool dedup, severity mapping, ranked
hotspots, a metrics schema) so a consumer receives one uniform shape.

Measured cost of that normalisation commitment (2026-05-30):

- **~3,002 LOC source / ~8,005 LOC tests** to shell out to 13 CLIs and merge their JSON.
- **17 adapters ≈ 1,511 LOC (half the source)** — each carries a per-tool `_to_sarif`
  normalisation shim, plus `aggregator.py` (SARIF consolidation), `severity.py`,
  `hotspots.py`, the `MetricSet` schema.
- The normalisation layer is **coupled to each tool's output schema**, so a major
  version bump on any of 13 tools can break its adapter's parser — the upgrade
  treadmill — and much of the 8k test LOC exists to catch exactly that drift.

Two findings reframe the requirement:

1. **There is no non-LLM consumer.** The only consumers of the structured output are
   LLM agents: the immediate review agent, and the future `intent-review` consumer
   (ADR-0010). Agents read heterogeneous tool output natively; a uniform machine
   schema is precisely what an agent does **not** need.
2. **The requirement is not "produce a uniform machine artifact."** It is *"make sure
   the right tools run on the changed code, and hand their output to the agent."*
   Interpretation is the agent's job, not the facade's.

## Decision

Replace the output-normalizing facade with a **thin invocation runner**.

The runner keeps only the stable, deterministic, silent-failure-prone work that is
worth being tested code:

- **select** applicable analyzers (by review domain/depth/language — ADR-0011 scheme,
  `selector.py` + `lang_select.py`),
- **invoke** each with its exact, load-bearing command line (the fiddly flags that fail
  *silently* when wrong: bandit `--quiet`, semgrep `--x-ignore-semgrepignore-files`,
  eslint `NODE_PATH`, trivy offline flags),
- **scope** to the diff,
- **run** with timeouts / availability detection (ADR-0019 contract retained),
- **capture** each tool's **raw** stdout/stderr/exit code into one **bundle**.

The runner **emits the bundle of native outputs** and stops. All interpretation —
severity judgement, cross-tool dedup, hotspot ranking — moves to the **consuming
agent**.

**Coupling principle:** couple to each tool's **invocation contract** (flags, exit
codes — stable, rarely changes), *not* its **output schema** (volatile, changes every
major version). This is the mechanical reason the upgrade treadmill disappears.

### Amendment to ADR-0010 (shared-format invariant)

ADR-0010 split review into two same-format skills (`code-review` + `intent-review`)
emitting a **shared SARIF schema** so a future consumer LLM could read both. That
invariant is **amended**: the future consumer is an LLM that **dedups by judgment**
(which ADR-0010 itself deemed sufficient when it rejected mechanical cross-aggregation).
A judgment-based consumer does **not** need a shared mechanical schema — it can read
`code-review`'s raw bundle **and** `intent-review`'s findings and reconcile by reasoning.
Therefore:

- `code-review` emits **raw bundles**, not SARIF.
- `intent-review` **may** still emit SARIF (free for it — the LLM is generating text
  anyway); it is no longer required to match `code-review`'s shape.
- No shared mechanical schema; no cross-skill aggregator.

## Consequences

- **~45% of source deleted** (~1,350 LOC): every `_to_sarif`, `aggregator.py`,
  `severity.py`, `hotspots.py`, `MetricSet`, the SARIF builders in `sarif_utils.py`.
  Tests fall from ~8k → ~2–2.5k (the per-adapter SARIF-correctness suites go with the
  normalisers). **~55% reused** — the *stable* half: subprocess runner, selection,
  language/diff detection, provisioning, config, CLI skeleton, and the invocation half
  of every adapter (each adapter shrinks to invoke + capture, ~15 LOC).
- **Upgrade-fragility removed** — nothing parses tool output, so a tool changing its
  format cannot break the runner; the agent reads the new format.
- **Output is heterogeneous by design.** The bundle is raw material, not a finished
  product.
- **Guard-rail: the runner must stay thin.** The moment it re-acquires normalising /
  ranking / scoring, it is the old facade again and must be rejected. Its remit ends at
  the invocation boundary.
- **Gap dispositions** (from the coverage dogfood; full mapping in
  `epic-analyzer-thin-runner.md`): **G3** (duration telemetry) is *retired* — it lived
  in the deleted metrics layer. **G1/G2/G7** are *reframed* (jscpd scope, FP filtering)
  as invocation-flags or agent-interpretation. **G5/G6/G8** become *cheap extensions*
  (oracle, JS semgrep rules, JS complexity analyzer) — and serve as the architecture's
  **validation criterion**: if adding a ruleset / analyzer / oracle is not near-trivial
  on the new design, the design is wrong.

## Alternatives considered

1. **Pure SKILL.md (no runner).** A skill that tells the agent which tools to run and
   how, with the agent invoking each via Bash. **Rejected.** It pushes 13 fiddly,
   *silently-failing* invocations onto per-run agent reconstruction (a wrong flag →
   zero findings → a false all-clear on a security review — the worst failure mode).
   This project has already paid to discover those landmines (bandit `--quiet` / F3,
   semgrep `--x-ignore`); prose is advisory and untestable, code is enforced and
   testable. A responsibly-reliable SKILL.md grows a setup script + run-all wrapper +
   exact-command recipes — i.e. an *untested* runner — so it converges on this decision
   anyway. (Mirrors ADR-0010's own rejection of "selection mapping in the prompt".)
2. **Keep the facade, stop normalising (each adapter passes raw through).** *Rejected.*
   Leaves every adapter still *structured around producing output* and the
   `AnalyzerOutput.sarif` contract intact, so the output-schema coupling — the actual
   fragility — has somewhere to keep living. Does not solve the stated problem.

## Risk

Heterogeneous output relies on per-tool agent competence. Mitigated: that is the
consumer's native mode, and the `intent-review` vision (ADR-0010) already assumes a
judgment-based consumer. The `unavailable`-vs-`error` contract (ADR-0019) is retained
so the agent can still tell "tool had nothing to scan" from "tool failed".
