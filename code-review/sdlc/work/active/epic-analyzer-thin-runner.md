---
id: epic-analyzer-thin-runner
kind: epic
project: code-review
status: active
children:
  - s0-contract-inversion-and-bundle
  - s1-migrate-adapters-and-emit-bundle
  - s2-skill-interpretation-and-golden-bundle
  - s3-js-semgrep-rules
  - s4-js-complexity-analyzer
sources: [post-coverage-eval-findings.md, vendor-js-semgrep-rules.md, g5-maintainability-oracle-repos.md, g8-js-complexity-cohesion-absent.md]
created: 2026-05-30
updated: 2026-05-30
tags: [architecture, runner, simplification, sarif, supersedes-facade]
---

# Epic — analyzer thin-runner re-architecture

Governed by **ADR-0020** (thin invocation runner replaces the normalizing facade).
Supersedes the gap-driven continuation of `epic-analyzer-polish` (now closed).

## Why

The analyzer layer is an **output-normalization-and-aggregation engine**: ~3,002 LOC
source / ~8,005 LOC tests to shell out to 13 CLIs and merge their JSON. Half the source
is per-tool SARIF normalisation (`_to_sarif` ×~8 + `aggregator`/`severity`/`hotspots`/
`MetricSet`), and that layer is coupled to each tool's *output schema* — the source of
the upgrade treadmill (any tool's major version can break its parser).

We established (ADR-0020) that **the only consumers are LLM agents**, which read
heterogeneous tool output natively. The normalisation layer serves a uniform-machine-
schema requirement that no consumer actually has. So we delete it.

## Goal

Cut the analyzer layer down to a **thin invocation runner**: select the right tools,
invoke them with their exact (silent-failure-prone) flags, scope to the diff, run, and
**capture raw output into a bundle** for the agent to interpret. Couple to each tool's
*invocation contract*, not its *output schema*.

**Validation criterion for the whole epic:** adding a JS ruleset (G6), a JS complexity
analyzer (G8), or a precision oracle (G5) must each be *near-trivial* on the new design.
If any is hard, the architecture is wrong.

## Target architecture (high level — detail co-located here until epic close)

**Kept (~55% reuse — the stable half):** `base.run_subprocess`, `selector` + `lang_select`
(tool selection / ADR-0011 scheme), `js_base` availability/JS-detect, `install`
(provisioning), `config`/`paths`/`diff`/`bundle`, the CLI skeleton, the **invocation
half** of every adapter, and the ADR-0019 `unavailable`-vs-`error` contract.

**Deleted (~45% — the fragile half):** every adapter `_to_sarif`, `aggregator.py`,
`severity.py`, `hotspots.py`, `MetricSet`, the SARIF builders in `sarif_utils.py`, and
the per-adapter SARIF-correctness test suites.

**New:** a **bundle** output type — a container of per-tool `{tool, raw stdout/stderr,
exit code, status}` — emitted by the CLI and read by the agent. `AnalyzerOutput` inverts
to raw-capture-first (drop `sarif`/`metrics`).

**Migration strategy:** contract-first **strangle**, not big-bang. s0 introduces the new
raw-capture contract + bundle; s1 migrates adapters and deletes the old layer; tests
migrate alongside so the green bar holds throughout.

## Candidate stories (sequence; tasks defined at Plan time)

- **s0 — contract inversion + bundle format.** Redefine `AnalyzerOutput` (raw-capture-
  first); define the bundle schema; retain selection + the ADR-0019 availability
  contract. Tests: bundle shape, availability contract preserved.
- **s1 — migrate adapters to invoke-and-capture + emit the bundle.** Planned 2026-05-30;
  s1-t1 re-split 2026-05-30 (6 tasks: s1-t0 type/status SoT **(done)**; s1-t1 5 subprocess
  Python adapters + `run_and_capture(env=)`; s1-t1b radon/vulture/cohesion library→CLI;
  s1-t1c schemathesis library→subprocess; s1-t2 4 JS adapters + G1; s1-t3 CLI emits bundle +
  delete the layer). Re-split rationale: 4 of the 9 "Python adapters" are in-process library
  calls, not subprocesses — migrating them is a library→CLI conversion (radon/vulture/
  cohesion) and, for schemathesis, a major rewrite with an auth/sandbox-under-subprocess
  design fork that warranted its own task. Delete every `_to_sarif` + `aggregator`/
  `severity`/`hotspots`/`MetricSet`/SARIF builders; each adapter → invoke + capture +
  exit-code/availability mapping. **CLI bundle-emission pulled in from s2** (operator
  decision 2026-05-30): deleting `aggregator` orphans the CLI's output path, so the switch
  and the teardown land atomically in s1-t3. Tests: per-adapter **invocation** correctness
  (bandit `--quiet`, semgrep `--x-ignore`, eslint `NODE_PATH`, trivy offline), raw capture,
  availability, golden bundle. **Folds in G1** (jscpd scope).
- **s2 — SKILL.md interpretation + golden-bundle hardening (re-scoped).** CLI emission now
  ships in s1; s2 teaches the agent (SKILL.md) to read each tool's native output and judge
  severity/dedup, and hardens the golden-bundle fixtures. **Folds in G2/G7** (vulture/knip
  FP handling → agent-interpretation guidance — decide at Plan).
- **s3 — G6: vendor JS semgrep rules. (done 2026-05-31)** Orthogonal coverage win, now cheap;
  closes the no-JS-SAST gap. Shipped `security-js.yaml` (js-eval CWE-95, js-innerhtml-xss
  CWE-79) for `[javascript, typescript]` as rule file + fixture + test, zero adapter change —
  the architecture-validation criterion ("near-trivial") proven. (Vendored JS/TS rules into
  the ruleset, not a new tool.)
- **s4 — G8: JS complexity analyzer. (done 2026-05-31)** Shipped `jscomplexity` reusing the
  vendored ESLint `complexity` rule (zero new dependency; radon-`cc` parity). Tool choice +
  scope in **ADR-0022**. Narrowed to **JS-only** mid-story (gate escalation): ESLint can't
  parse TS without the unvendored `@typescript-eslint/parser`; TS complexity + JS cohesion are
  documented limitations. New analyzer added with no existing-adapter change — G8
  architecture-validation confirmed.
- **s5 — G5: maintainability oracle.** Extend the analyzer-coverage QA harness with
  labelled coupling fixtures (pydeps `test_cycles`, depcruiser `__mocks__`) asserted
  against the **new raw output**.

s3–s5 double as the architecture's validation suite (each should be small).

## Retired

- **G3 (duration telemetry 0.00s)** — lived in the deleted metrics layer; not fixed.

## Source

Compiled from the 2026-05-30 design discussion + coverage-dogfood raw notes
(`post-coverage-eval-findings.md` G1–G5; `vendor-js-semgrep-rules.md` G6;
`g8-js-complexity-cohesion-absent.md` G8; `g5-maintainability-oracle-repos.md` G5).
