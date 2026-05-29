---
id: s1-t0-adr-node-range-and-js-pins
kind: task
project: code-review
status: done
parent: s1-js-toolchain-manifest
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [node, javascript, pins, adr, stack-pins]
notes: |
  Delivered ADR-0017 (co-located in work/active until epic close) + stack-pins.md
  (Node row + Node/JS toolchain pin table). Verify PASS. Review MINOR-ONLY:
  - [APPLIED] Minor: "depcruiser 16 breaks on Node >=22" was unverified — F1 only
    shows the break on Node 24. Softened to "modern Node (seen on Node 24); lower
    bound unconfirmed; s3 confirms" in both ADR and stack-pins.
  - [APPLIED] Minor: clarified that npm caret `^N` is a deliberate major-bounded
    floor (differs from Python's unbounded `>=`), so s1-t1 keeps `^9` not `>=9`.
  - [FIXED] Nit: un-wrapped the skill-root code-path span that rendered broken.
  - [DROPPED] Nit: ADR vs stack-pins locked-patch column phrasing differs
    cosmetically; not worth churn.
---

# s1-t0 — ADR: Node version range & JS toolchain pins

## Outcome

An accepted ADR (ADR-0017) records the supported Node range and the pinned
versions of the five npm packages the JS/TS analyzers depend on, chosen to work
across **both Node 20 LTS and Node 22 LTS** (operator decision 2026-05-29).
`stack-pins.md` gains the Node range + the five tool pins. This is the
hard-stop runtime/stack decision the rest of s1 builds on; operator approves.

## Acceptance criteria

### Scenario: ADR records the range, pins, and lockfile location
- **Given** the docs after this task
- **Then** ADR-0017 states: supported Node range = **20 LTS and 22 LTS**
  (matrix-tested); pins for `eslint`, `knip`, `jscpd`, `dependency-cruiser`,
  `@microsoft/eslint-formatter-sarif` chosen to install + run on both majors;
  the lockfile lives at the **skill root** (`.claude/skills/code-review/`); and
  Node tooling is **not** shipped in the wheel (source-checkout / setup.sh only).

### Scenario: depcruiser cross-Node validation is delegated to s3
- **Given** depcruiser 16 breaks on Node ≥22 (F1)
- **Then** ADR-0017 pins a depcruiser version intended to work on both majors and
  explicitly delegates final cross-Node validation (and any pin bump within this
  lockfile) to **s3-depcruiser-node-compat**.

### Scenario: stack-pins.md updated
- **Given** `sdlc/docs/architecture/stack-pins.md`
- **Then** the Node row records "20 LTS + 22 LTS (matrix)" and a JS-tooling table
  lists the five pins, so rule #1b reconciliation has a source of truth.

## Test specification

Decision artefact — no code test. Verification is by inspection of ADR-0017 and
`stack-pins.md`. Operator approval of ADR-0017 is required before s1-t1 (the
manifest) is generated, since the pins are load-bearing for the lockfile.
Optional: a `test_stack_pins_lists_node_tools` assertion if a greppable check is
wanted (decide during execution; not mandatory for a decision task).
