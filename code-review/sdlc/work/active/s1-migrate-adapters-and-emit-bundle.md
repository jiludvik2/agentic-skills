---
id: s1-migrate-adapters-and-emit-bundle
kind: story
project: code-review
status: active
parent: epic-analyzer-thin-runner
children:
  - s1-t0-type-consolidation-and-status-sot
  - s1-t1-migrate-python-adapters
  - s1-t1b-migrate-library-adapters
  - s1-t1c-migrate-schemathesis
  - s1-t2-migrate-js-adapters
  - s1-t3-cli-bundle-and-delete-sarif-layer
sources: [epic-analyzer-thin-runner.md, adr-0020-thin-invocation-runner.md, s0-contract-inversion-and-bundle.md]
created: 2026-05-30
updated: 2026-05-30
tags: [migration, adapters, bundle, strangle, supersedes-facade]
---

# Story s1 — migrate adapters to invoke-and-capture + emit the bundle

Governed by **ADR-0020**. Second story of `epic-analyzer-thin-runner`. This is the
**switch + teardown** half of the strangle: s0 built the new rail (`CaptureOutput`,
`run_and_capture`, `ReviewBundle`, `review-bundle.v1.json`) purely additively; s1 moves
every adapter onto it, points the CLI at the bundle, and **deletes the normalisation
layer**. The green bar holds throughout — tests migrate alongside their code.

## Sequencing decision (operator-approved 2026-05-30)

The epic originally split "migrate adapters" (s1) from "CLI emits bundle" (s2). Deleting
`aggregator.py` in s1 **orphans the CLI's only output path**, so CLI bundle-emission is
pulled into **s1-t3** (delete the layer and switch the CLI in one atomic task — no
intermediate SARIF-bridge scaffolding). **s2 shrinks** to SKILL.md interpretation guidance
+ golden-bundle hardening (re-scope the epic's s2 accordingly).

## Scope (what changes)

- **Adapter return type inverts** to raw-capture-first. Every adapter `run()` returns a
  raw capture (the s0 `CaptureOutput`, consolidated with the to-be-deleted `AnalyzerOutput`)
  via `run_and_capture` — preserving its **exact invocation** (flags, cwd/env, tolerated
  exit codes) and its **ADR-0019 availability** pre-flight, dropping all output parsing.
- **Delete the fragile half:** every adapter `_to_sarif` (bandit, vulture, pydeps,
  depcruiser, jscpd, knip, schemathesis_), the SARIF builders in `adapters/sarif_utils.py`,
  `aggregator.py` (202), `severity.py` (39), `hotspots.py` (116), `MetricSet`, and the
  `AnalyzerOutput.sarif`/`metrics` fields — plus their dedicated test suites.
- **CLI emits the `ReviewBundle`** (s1-t3): `_run_analyzers` collects per-tool captures →
  `ReviewBundle(request, outputs)` → `bundle_to_json`; validate against
  `review-bundle.v1.json` (replacing the `review-response.json` path); map the process
  exit code from capture statuses.
- **Keep (the stable half):** `base.run_subprocess`, `js_base` availability/JS-detect,
  `selector`/`lang_select` (ADR-0011), `install`/provisioning, `config`/`paths`/`diff`,
  the CLI skeleton, the **invocation half** of every adapter, the ADR-0019 contract.

## Acceptance criteria (story-level)

- No `_to_sarif` / `aggregator` / `severity` / `hotspots` / `MetricSet` / SARIF-builder
  code remains; `grep` confirms zero references outside deleted-test history.
- Every one of the 13 adapters returns a raw capture and is covered by an **invocation
  correctness** test (the argv it builds), a **raw-capture** test, and an **availability**
  test. Load-bearing flags are pinned by assertion (see task specs).
- `polyreview run` emits a `review-bundle.v1.json`-valid bundle on a fixture (golden test);
  process exit code reflects capture statuses (any `error` → non-zero).
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` all clean.
- The three s0 story-level Minors are absorbed: shared status SoT (s1-t0); bundle
  `timeout`-capture coverage (s1-t3); timeout-test loop-teardown cleanup (s1-t3).

## Deferred (BDD-deferral annotations — out of scope for s1)

- **SKILL.md agent-interpretation guidance** + golden-bundle hardening — **s2**.
- **G2/G7** vulture/knip false-positive handling (invocation flag vs agent guidance) —
  decide at **s2** plan.
- **G6** vendor JS semgrep rules — **s3**. **G8** JS complexity — **s4**. **G5** oracle — **s5**.
- **Diff-path resolution** (`resolve_diff_paths` repo-relative vs `cli.py` cwd-abspath) —
  fix opportunistically during s1-t3 if it falls out of the CLI rewrite; else carry to s2.

## Re-split decision (operator-approved 2026-05-30)

Scoping s1-t1 surfaced a planning defect: only **5 of the 9 Python adapters are
subprocess-based** (bandit, semgrep, gitleaks, trivy, pydeps). The other 4 are **in-process
library calls** with no subprocess invocation to "keep" — migrating them means choosing a
CLI invocation contract per tool, and **schemathesis** (in-process, auth- + sandbox-isolated
~10K adapter) is a major rewrite to a `schemathesis run` subprocess with auth/sandbox
semantics not dictated by the spec (an autonomy-gate fork). s1-t1 is therefore split into
three, keeping one-commit granularity and isolating the design fork:

- **s1-t1** — the 5 subprocess Python adapters + add `env=` to `run_and_capture`.
- **s1-t1b** — radon / vulture / cohesion: library → CLI subprocess conversion.
- **s1-t1c** — schemathesis: in-process library → `schemathesis run` subprocess (design the
  auth/sandbox-under-subprocess approach; highest risk).

`s1-t2`/`s1-t3` ids are unchanged (the `-t1b`/`-t1c` suffix inserts after `s1-t1` without
renumbering). The story-level AC "all 13 adapters return a raw capture" is unchanged — it is
now satisfied across s1-t1 + s1-t1b + s1-t1c + s1-t2.

## Tasks

- **s1-t0** — type consolidation + ADR-0019 status single-source-of-truth. **(done)**
- **s1-t1** — migrate the 5 subprocess Python adapters + `run_and_capture(env=)`.
- **s1-t1b** — migrate radon / vulture / cohesion (library → CLI subprocess).
- **s1-t1c** — migrate schemathesis (library → subprocess; auth/sandbox design).
- **s1-t2** — migrate the 4 JS adapters (folds in G1: jscpd language scope).
- **s1-t3** — CLI emits the bundle + delete the SARIF normalisation layer.
