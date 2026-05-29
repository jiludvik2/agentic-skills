---
id: adr-0014-multi-agent-rename
kind: decision
project: code-review
status: accepted
parent: s3-multi-agent-rename
sources: [s3-multi-agent-rename.md, adr-0012-pypi-publication.md]
created: 2026-05-29
updated: 2026-05-29
tags: [naming, multi-agent, pypi, agents-md, packaging]
---

# ADR-0014: Rename the PyPI distribution + console binary to `polyreview`; adopt AGENTS.md

## Status

Accepted. Refines ADR-0012 (PyPI publication) by changing the distribution name only; ADR-0012's publication mechanism (Trusted Publishers / OIDC, three-job `release.yml`, TestPyPI-for-rc routing) stays in force. The Trusted Publisher binding name moves from `claude-code-review` to `polyreview` on both registries.

## Context

The tool ships as an Agent Skill at `.claude/skills/code-review/SKILL.md`. As of 2025-12-18 the Agent Skills standard was open-sourced, and GitHub Copilot, VS Code, Cursor, Codex, Gemini CLI, Goose, and ~40 other agents now read `.claude/skills/`, `.github/skills/`, and `.agents/skills/` interchangeably. The existing skill bundle is already consumed by non-Claude agents today with no change.

That makes the `claude-` prefix on the **PyPI distribution name** the only real vendor coupling left in the install path. `pip install claude-code-review` reads as "an Anthropic-only tool", which is misleading for a deterministic multi-analyzer review CLI that is agent-agnostic. PEP-423 is explicit that the distribution name need not equal the import name (`python-dateutil` → `import dateutil`), so the distribution can be renamed without touching internal imports.

A second gap: the repo carries `CLAUDE.md` as its agent-instructions file, but the cross-vendor convention is `AGENTS.md` (Linux Foundation-stewarded, 60k+ repos, native readers including Copilot, Codex, Cursor, Aider, GitLab Duo). A Copilot or Codex user cloning the repo looks for `AGENTS.md`, not `CLAUDE.md`.

## Decision

1. **Rename the PyPI distribution and console binary** `claude-code-review` → **`polyreview`**. Short, coined, vendor-neutral, language-neutral; joins the Ruff/Semgrep/Bandit naming family. Verified PyPI-available 2026-05-29. The console-script entry point target is unchanged (`code_review.cli:app`); only the script *name* changes.
2. **Add `AGENTS.md`** at the repo root as the canonical cross-agent policy file (agents.md format). **Shrink `CLAUDE.md`** to a one-line `See AGENTS.md.` redirect — Claude Code reads CLAUDE.md as-is, so the redirect keeps Claude working while making AGENTS.md the single source of truth. No policy content is duplicated between the two.
3. **Move the Trusted Publisher binding** to `polyreview` on PyPI and TestPyPI. The `release.yml` `test-dist` smoke step and workflow `name:` update to the new binary (executed in s3-t1).

## Kept unchanged (each names a capability, not the vendor)

- **Python import name `code_review`.** Renaming it would break every internal import for zero user benefit; PEP-423 + the python-dateutil precedent endorse the dist≠import asymmetry.
- **Skill bundle path `.claude/skills/code-review/` and skill folder name.** The Agent Skills spec only requires `frontmatter.name == directory_name`, not `skill-name == package-name`. All major agents read this path already.
- **Monorepo subdirectory `code-review/`.** Names a capability; renaming would break every SDLC artefact path and CI path filter.
- **Release-tag prefix `code-review-v*`** (and the `publish` job's `^code-review-v…$` validation regex). The tag stream names the release line/capability, identical reasoning to the folder name. Consequence: package `polyreview` is released under `code-review-v*` tags — a deliberate, recorded asymmetry, not an oversight. Revisitable in a future story if it proves confusing.

## Consequences

- One atomic rename commit (s3-t1) touches `pyproject.toml`, `code_review/__init__.py`, `release.yml`, `README.md`, `SKILL.md`, the release runbook, ADR-0012 (cross-ref), and the affected tests — the tree never sits half-renamed.
- The first PyPI release must happen **after** this rename; otherwise the package publishes under the wrong name. The Trusted Publisher must be (re)configured for `polyreview` before the first real tag — operator-side, off-repo.
- `code_review.__version__` resolves via `importlib.metadata.version("polyreview")`; an editable/installed environment whose dist metadata still says `claude-code-review` would raise `PackageNotFoundError` until reinstalled. Acceptable: the rename lands before first publication, and the source-checkout fallback in `__init__.py` already guards the not-installed case.

## Deferred follow-up (not a task in this story)

Publish a `claude-code-review` 0.x.y **redirect meta-package** depending only on `polyreview`, so anyone who already typed the old name still lands on the tool. Depends on `polyreview` being published first (operator-side). Captured in the release runbook's "Rename history".

## Alternatives considered

- **`python-code-review`** — rejected: PEP-423 reads `python-` as "a library for Python users", not "a tool that reviews Python"; misleading for a multi-language reviewer.
- **Keep `claude-code-review`, add a redirect later** — rejected as the primary name: it keeps the misleading vendor framing on the canonical install path. Retained only as the deferred redirect package above.
- **Rename the import name / skill folder / tag prefix too** — rejected: high churn, breaks internal imports and SDLC/CI paths, zero user benefit (see Kept unchanged).

## Cross-references

- ADR-0012 (PyPI publication) — publication mechanism; this ADR changes only the bound distribution name.
- `s3-multi-agent-rename.md` — the story; `s3-t1` executes the rename, `s3-t2` adds AGENTS.md.
- `sdlc/docs/runbooks/release.md` — Trusted Publisher binding + rename history (updated in s3-t1).
