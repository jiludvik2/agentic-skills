---
id: s2-aggregator-and-severity-mapping
kind: story
project: code-review
status: done
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26
---

# s2 — Aggregator with dedup and SDLC severity mapping

## Summary

Consolidate per-analyzer SARIF outputs into a single review-level SARIF report, deduplicating findings that multiple analyzers report on the same location. Map SARIF `level` + `properties.severity` into the SDLC's Critical / Important / Minor / Nit taxonomy (lines 166–169 of SDLC.md). Produce a ranked-hotspots list (per-file composite score) for the sub-agent's auto-remediation step (rule #25).

The aggregator runs inside the CLI from s0 — given multiple `--analyzer` arguments, the CLI fans out, then the aggregator consolidates before emitting the final consolidated document.

## Use Case

- **As a** Reviewer sub-agent (s5) processing the CLI's output
- **I want to** receive a deduplicated SARIF report with each finding tagged in the SDLC's severity taxonomy, plus a per-file ranked hotspot list
- **so that** I can apply rule #25's auto-remediation rules (file Critical/Important as fix tasks, append Minor to notes, drop Nit) without writing per-analyzer parsing logic, and so that I can pick the top-N files to refactor first

## Acceptance Criteria

### Scenario: Two analyzers flagging the same line produce one consolidated finding with multiple sources

- **Given** Semgrep and Bandit both produce findings at `src/auth.py:47` for related vulnerability classes (both tag CWE-89)
- **When** the aggregator runs
- **Then** the consolidated SARIF contains exactly one `result` at that location, with `properties.sources` listing both `semgrep` and `bandit`, and the highest severity from either source preserved in the merged result

### Scenario: Findings within a 3-line tolerance on the same file and same CWE are merged

- **Given** Semgrep reports a finding at `src/auth.py:47` and Bandit reports the equivalent at `src/auth.py:49`, both tagged CWE-89
- **When** the aggregator runs
- **Then** they merge into a single finding (lower line number wins), with `properties.original_locations` listing both line numbers for audit

### Scenario: Findings without a shared CWE do not merge even at the same line

- **Given** two findings at `src/auth.py:47` with different CWE values
- **When** the aggregator runs
- **Then** both findings appear in the consolidated output as separate `result` entries; CWE is the merge anchor, not file+line alone

### Scenario: Severity mapping applies the SDLC taxonomy

- **Given** consolidated findings with mixed `level` and `properties.severity` values
- **When** the severity mapper runs
- **Then** each finding gains a `properties.sdlc_severity` field with one of `critical`, `important`, `minor`, `nit`, mapped as: `level==error` ∨ `properties.severity in {critical}` → `critical`; `level==warning` ∧ `properties.severity in {important, high}` → `important`; `level==warning` (no severity) → `minor`; `level==note` ∨ `properties.severity in {nit, info}` → `nit`. The mapping table lives in `code_review/severity.py`, not inline in adapter code.

### Scenario: Ranked hotspots reflect a multi-axis composite score

- **Given** consolidated findings across several files plus the merged MetricSet from complexity/coupling/cohesion analyzers
- **When** the aggregator computes hotspots
- **Then** each touched file gets a `composite_score` and a list of contributing factors (severity-weighted finding count, cyclomatic complexity, fan-in+fan-out, inverse cohesion if available); the output is a `ranked_hotspots` list of `{file, composite_score, factors}` sorted descending. Weights live in `capabilities.json` or a sibling `code-review.toml`, not in code.

### Scenario: Per-task and story-level scopes produce different hotspot scopes

- **Given** a CLI invocation with `--scope per-task` and another with `--scope story-level` against the same diff
- **When** both complete
- **Then** the per-task hotspots are restricted to files in the diff; the story-level hotspots include cross-task patterns (e.g., a fan-out finding that only emerges when looking at all files together) and may include files not directly modified

### Scenario: CWE taxonomy is referenced via SARIF taxa, not free-form tags

- **Given** a finding tagged with a CWE identifier
- **When** I inspect the consolidated SARIF
- **Then** the CWE reference appears in the result's `taxa` array (per SARIF 2.1.0's taxonomy mechanism), the run declares the CWE taxonomy in `tool.driver.supportedTaxonomies`, and the same finding does not duplicate the CWE id as a free-form `tag`

### Scenario: Operator can override aggregation thresholds without code changes

- **Given** `.claude/skills/code-review/code-review.toml` sets `dedup.line_tolerance = 5` and overrides one severity mapping entry
- **When** the aggregator loads config and runs
- **Then** the line tolerance and severity mapping reflect the config; defaults apply for unset values

### Scenario: Consolidated output validates against the response schema from s1

- **Given** a completed aggregation run
- **When** the consolidated JSON is validated against `.claude/skills/code-review/schemas/review-response.json`
- **Then** validation succeeds; all required fields are present; SARIF substructure validates against the SARIF 2.1.0 schema

## Test specification

- **Dedup correctness test** — fixture SARIF inputs from 3 mock analyzers with planned overlaps, assert exact dedup outcomes (same-line, near-line, different-CWE).
- **Severity mapping table test** — exhaustive table-driven test covering each input combination → expected SDLC severity.
- **Composite score test** — golden-file test: given known SARIF + MetricSet inputs, assert ranked-hotspots output matches expected JSON.
- **Scope-difference test** — same diff, two runs with different `--scope`, assert hotspots reflect the scope (per-task restricted to changed files; story-level may include unchanged files).
- **Config override test** — load a `code-review.toml` with overrides, assert behaviour reflects the overrides.
- **CWE taxonomy reference test** — fixture with a known CWE-tagged finding, assert the SARIF result references CWE via `taxa`, the run declares `supportedTaxonomies`, and no duplicate `tags` entry exists.
- **Response-schema validation test** — round-trip a consolidated output through the s1 response schema; assert no required fields are dropped during dedup.

## Out of scope (deferred to later stories)

- Sub-agent's actual fix-task spawning logic (s5) — this story produces the input the sub-agent will consume.
- Cross-review historical trending (e.g., "Critical findings over the last 10 commits") — out of scope for this epic; filesystem-walking trend scripts are a future addition.
- Architectural-drift detection across stories — story-level scope produces useful per-review output but doesn't yet do cross-story trend analysis.
- Custom severity mapping per-project beyond the skill's `code-review.toml` — single skill-level config.
