---
id: adr-0007-package-bundled-contracts
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [adr-0005-sandbox-compatibility.md, adr-0006-sarif-canonical-format.md, architecture-reviewer-subagent.md]
created: 2026-05-27
updated: 2026-05-27
tags: [packaging, resources, deployment, sandbox]
---

# ADR-0007: capabilities.json and JSON schemas are bundled in the Python package, resolved via `__file__`

## Status

Accepted. Supersedes the implicit "skill directory owns the contracts" model documented in the s1 SKILL.md. Direct consequence of ADR-0005 (sandbox) colliding with the s0/s1 layout.

## Context

The deterministic analyzer layer carries non-code resources: the static capability declaration (`capabilities.json`) and four JSON Schemas (`sarif-2.1.0.json`, `capabilities.json` validator, `review-request.json`, `review-response.json`). The s0/s1 implementation scattered these across three homes:

- `.claude/skills/code-review/capabilities.json` — read by `cli.py`, `config.py`, **and** `hotspots.py`;
- repo-root `/schemas/` — where `semgrep.py` reads `sarif-2.1.0.json` via `Path(__file__).parent.parent.parent`, and where most tests read all four;
- `code_review/schemas/review-response.json` — read by `cli.py` (the half-done relocation that prompted this review).

Two problems converge on this layout:

1. **Sandbox write-block (ADR-0005).** The operator's strict sandbox confines writes to CWD but the host `denyWithinAllow` policy blocks all writes under `.claude/skills/`. Every edit to `capabilities.json` during development requires a sandbox bypass — recurring friction, already worked around once for the `review-response.json` schema.
2. **Install-path fragility.** `semgrep.py` reaching the repo root via `parent.parent.parent` resolves correctly only for an editable install run from the repo tree. Any non-editable install breaks it. (Tracked as the "`_SKILL_DIR` sibling-path assumption breaks for a wheel install" debt.)

The decisive fact: **nothing outside the `code_review` package reads these files at runtime.** The `reviewer` sub-agent never opens them — it shells out to `python -m code_review.cli` and consumes `--capabilities` and the CLI's consolidated JSON. So the skill directory does not need the contracts to *execute*; only the package does.

## Decision

**The `code_review` Python package is the single source of truth for `capabilities.json` and all four JSON schemas.** They live at `code_review/capabilities.json` and `code_review/schemas/*.json`, and every package reader resolves them relative to `Path(__file__)`, never the repo root and never the skill directory.

1. **One home, package-relative reads.** `cli.py`, `config.py`, `hotspots.py` read `capabilities.json` from `Path(__file__).parent[…]`; adapters read schemas the same way. No reader references `.claude/skills/` or the repo root for a contract.
2. **No skill-directory copies.** The skill dir keeps `SKILL.md`, `scripts/`, `agents/reviewer.md`, and (gitignored) `cache/` + `node_modules/` — but not the contracts. SKILL.md documents that the capability declaration is bundled in the package and surfaced via `--capabilities`.
3. **Deployment = installing the package.** `scripts/setup.sh`'s `uv sync` is how the contracts reach a runtime; there is no copy-into-skill-dir step. Bundling is enforced as wheel package-data so a non-editable install carries them too.
4. **Repo-root `/schemas/` is removed.** It was scratch, neither sandbox-blocked nor part of any install unit.

This establishes a standing rule: **package code reads its own resources via `Path(__file__)`; resources a tool needs at runtime are package data, not skill-directory assets.**

## Consequences

- Edits to `capabilities.json` and schemas no longer touch `.claude/skills/`, so they happen inside the sandbox with no bypass (satisfies ADR-0005 without widening `allowWrite`).
- The wheel-install path break is fixed, and the "three duplicate `_SKILL_DIR` constants" debt collapses: `config.py` and `hotspots.py` drop `_SKILL_DIR` entirely; `cli.py` keeps a minimal one only to locate the operator's `code-review.toml`.
- SKILL.md's contract-location wording must change (it currently implies skill-dir-relative paths) — recorded here as the reason.
- The skill directory is no longer self-contained for *contracts* (it remains self-contained for *offline execution* per ADR-0005, which is about caches/binaries). Anyone inspecting the skill dir for `capabilities.json` is redirected by SKILL.md to `--capabilities`.
- **Out of scope / follow-up:** `code-review.toml` is operator runtime config, not a package resource; it stays external. Where the CLI should look for it (skill dir vs. the reviewed project's CWD) is a separate decision, deferred.
