---
id: s2-skill-interpretation-and-golden-bundle
kind: story
project: code-review
status: done
parent: epic-analyzer-thin-runner
children:
  - s2-t0-diff-path-resolution
  - s2-t1-remove-dead-sarif-schema
  - s2-t2-golden-bundle-hardening
  - s2-t3-skill-md-interpretation-guidance
sources: [adr-0020-thin-invocation-runner.md, epic-analyzer-thin-runner.md, intent-review-requirements.md]
created: 2026-05-31
updated: 2026-05-31
tags: [skill, interpretation, golden-bundle, diff-path, cleanup, capstone]
---

# Story s2 — SKILL.md interpretation guidance + golden-bundle hardening

## Why

The strangle (s1) made `polyreview run` emit a raw `review-bundle.v1.json`: the request
echo plus one verbatim `CaptureOutput` per tool. Interpretation moved *out* of the runner
and *onto the consuming agent* (ADR-0020). But the agent was never told **how** to interpret
the bundle: SKILL.md still documents only invocation/install/taxonomy. The agent is now handed
heterogeneous output — JSON (bandit, radon, pydeps, jscpd, knip, depcruiser), SARIF (semgrep,
trivy, eslint), and plain text (vulture, cohesion, gitleaks) — with no per-tool reading guide,
no severity cues, and no dedup-by-judgment instruction. That guidance is this story's core
deliverable; the runner stays thin, the *interpretation contract* lives in prose where the
agent reads it.

This story also clears the two carry-overs s1 flagged for s2 and folds in the epic's
plan-time G2/G7 disposition.

## Scope

1. **Per-tool interpretation guidance in SKILL.md** (capstone, s2-t3) — teach the agent to read
   each tool's native output, judge severity, and dedup across tools by judgment (ADR-0010 /
   ADR-0020: no mechanical aggregator). Folds in **G2/G7** (vulture/knip false-positive handling)
   as concise inline FP notes per the operator-approved plan-time disposition (not a separate
   heavyweight section — keeps the guidance where the agent reads it).
2. **Golden-bundle hardening** (s2-t2) — a recorded golden bundle fixture (all three output
   formats × all four ADR-0019 statuses) asserted byte-equal against the CLI's emitted output
   (serialization-drift regression guard), plus edge-case coverage.
3. **Diff-path resolution fix** (s2-t0, carry-over) — `resolve_diff_paths` anchors on the git
   repo root, not `Path.cwd()`, so repo-relative changed-file paths resolve from any subdir.
4. **Remove the dead `sarif-2.1.0.json` schema** (s2-t1, carry-over) — operator decision
   2026-05-31: **remove**. Nothing in `code_review/` loads it after `sarif_utils` was deleted;
   intent-review vendors its own SARIF schema when that sibling project is bootstrapped.

## Acceptance criteria

- SKILL.md carries an "Interpreting the bundle" section covering **every analyzer in the
  adapter registry**, with each tool's output format, how to read it, and severity cues; plus
  cross-tool dedup-by-judgment guidance and vulture/knip FP notes (G2/G7).
- A doc-structure test fails if a registered analyzer is missing from the interpretation
  guidance (guidance cannot silently drift from the adapter set).
- A recorded golden bundle fixture validates against `review-bundle.v1.json` and the CLI emits
  a byte-equal bundle for the recorded inputs (regression guard); edge cases covered
  (all-`unavailable` → exit 0, non-UTF8/control-char stdout round-trips verbatim, empty
  `outputs`).
- Running a diff-scoped review from a repo **subdirectory** resolves changed-file paths against
  the repo root (RED reproduces the subdir mis-resolution; GREEN fixes it).
- `code_review/schemas/sarif-2.1.0.json` is gone; the 3 packaging-test pins are dropped;
  `grep -r sarif-2.1.0` is clean in `code_review/`; the intent-review handoff doc notes the
  schema relocation.
- `uv run pytest` (+ integration), `uv run ruff check .`, `uv run mypy code_review` clean.

## Guard-rail

The runner stays **thin** (ADR-0020): all interpretation guidance lands in SKILL.md prose, not
in code. No severity-mapping table, ranking, or dedup logic re-enters `code_review/`. If a task
finds itself adding scoring code, stop — that is the deleted facade trying to come back.

## Task sequence

- **s2-t0** — diff-path resolution fix (pure code; smallest; real bug).
- **s2-t1** — remove dead `sarif-2.1.0.json` schema + packaging pins (cleanup).
- **s2-t2** — golden-bundle fixture + edge-case hardening (test-heavy).
- **s2-t3** — SKILL.md per-tool interpretation guidance (capstone; folds G2/G7).

## Source

Compiled 2026-05-31 from `epic-analyzer-thin-runner.md` (s2 candidate-story description +
G2/G7 fold-in), the s1 story-level review carry-overs in `STATE.md`, and ADR-0020.
