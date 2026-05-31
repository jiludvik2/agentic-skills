---
id: s4-t0-adr-js-complexity-tool
kind: task
project: code-review
status: done
parent: s4-js-complexity-analyzer
sources: [epic-analyzer-thin-runner.md, g8-js-complexity-cohesion-absent.md]
created: 2026-05-31
updated: 2026-05-31
notes: |
  ADR-0022 written, status accepted, recording operator-approved option 1 (reuse
  vendored ESLint complexity rule, zero new dependency). Verifier PASS, reviewer
  MINOR-ONLY. All 3 Minors applied (not just noted): added ADR-0019 to sources +
  an explicit "no-flat-config unavailable path does not apply" interaction
  paragraph (the adapter ships its own config); restated the threshold-0
  full-coverage mechanism at the decision point; deferred the unavailable/error
  mapping to s4-t1 explicitly. ADR stays co-located in work/active/ until epic
  close. No code/test changes.
tags: [adr, complexity, javascript, tool-selection, cohesion]
---

# Task s4-t0 — ADR-0022: JS complexity tool selection

## Outcome

An accepted ADR records the JS/TS complexity tool decision (resolving the SDLC rule #11/#15
stack hard-stop), the `radon cc`-parity scope, and the JS cohesion limitation. No code.

## Hard-stop note

This task resolves a stack/tooling hard-stop. The operator's approval of the s4 plan (which
names the recommended tool) is the in-scope decision; this task formalises it as an ADR. If
the operator's approval changed the tool from the recommended option, this ADR records the
chosen one.

## ADR content (draft `adr-0022-js-complexity-tool.md`, co-located in work/active per the
Co-locate convention; moves to `sdlc/docs/decisions/` at epic close)

- **Status:** Accepted.
- **Context:** `maintainability/complexity` is Python-only (`radon cc --json`); G8 needs
  JS/TS parity. Pins are silent on a JS complexity tool. The radon adapter runs only `cc`,
  so the parity target is per-function cyclomatic complexity, nothing richer.
- **Decision:** the chosen tool + invocation approach. Recommended: **reuse the vendored
  ESLint `complexity` core rule** via an adapter-supplied complexity-only flat config at
  threshold `0` (reports every function's complexity), captured raw (ADR-0020). Record why
  over `eslintcc`/`ts-complex` (zero new dependency; no ESLint-version divergence; parity,
  not excess). Record the analyzer id chosen (recommended `jscomplexity`).
- **Cohesion limitation:** no maintained, thin, JSON-emitting JS/TS cohesion (LCOM) tool
  fits the vendored-npm + raw-capture model; JS cohesion is a **declared known limitation**,
  not implemented. State this explicitly so it is not read as an oversight.
- **Consequences:** new analyzer slots into the existing ADR-0011 selection scheme under
  `maintainability/complexity` with no scheme change; if reuse-ESLint is chosen, no new pin;
  if a new npm tool is chosen, ADR-0017 pins it (s4-t1).
- **Provenance of any vendored config:** the complexity flat-config the adapter ships is
  hand-authored, MIT, same policy as the depcruiser config and the semgrep ruleset.

## Acceptance criteria

- `adr-0022-js-complexity-tool.md` exists in `sdlc/work/active/`, `status: accepted`, with:
  decision + rationale (chosen tool vs the two alternatives), cc-parity scope, cohesion
  limitation, and selection-scheme impact.
- ADR number 0022 confirmed unused at execution (highest existing is 0021).
- The epic `sources:`/cross-references note ADR-0022 where appropriate.
- No code or test changes in this task (ADR only).

## Test specification

No tests (ADR-only task). The decision is validated by s4-t1's implementation tests, which
must match what this ADR specifies (tool, invocation, parity scope).
