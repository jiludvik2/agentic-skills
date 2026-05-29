---
id: s3-multi-agent-rename
kind: story
project: code-review
status: active
parent: epic-deployment-readiness
sources: [multi-agent-research-2026-05-29, audit-claude-coupling-2026-05-29]
children: [s3-t0-adr-0014-multi-agent-rename, s3-t1-rename-pypi-and-binary-and-docs, s3-t2-agents-md-and-claude-md-redirect]
created: 2026-05-29
updated: 2026-05-29
tags: [naming, multi-agent, pypi, agents-md, copilot]
---

# s3 — Multi-Agent Rename + AGENTS.md

## Summary

Drop the `claude-` prefix from the PyPI distribution and console binary so the tool can ship to GitHub Copilot, Cursor, Codex, and other AI coding agents without misleading vendor framing. Rename to **`polyreview`** — short, coined, vendor-neutral, language-neutral, joins the Ruff/Semgrep/Bandit naming family on PyPI. Add **`AGENTS.md`** at the repo root as the canonical cross-agent instructions file (~60k repos using the standard; native readers include Copilot, Codex, Cursor, Aider, GitLab Duo, and others). Shrink `CLAUDE.md` to a one-line redirect.

Research findings reframing the question — captured here because they're load-bearing for the story scope:

- The Agent Skills standard was open-sourced by Anthropic 2025-12-18. **GitHub Copilot, VS Code, Cursor, Codex, Gemini CLI, Goose, and ~40 other agents now read `.claude/skills/`, `.github/skills/`, and `.agents/skills/` interchangeably.** The current skill bundle at `.claude/skills/code-review/SKILL.md` IS ALREADY consumed by Copilot today — no skill-side move needed.
- The Python import name `code_review` stays unchanged. PEP-423 explicitly notes distribution name ≠ import name (cf. `python-dateutil` → `import dateutil`).
- The monorepo subdirectory `code-review/` stays unchanged. It names a capability, not a vendor.

## Depends on

- `s2-packaging-hardening` closed (commit `0279c9c`). The release workflow, dep policy, importlib-metadata version source, LICENSE bundling — all already in shape to absorb the rename without rework.

## Use case

- **As a** tool author who plans to support multiple AI coding agents
- **I want to** publish under a vendor-neutral name + ship a cross-agent instructions file
- **so that** users on GitHub Copilot, Cursor, Codex, etc. can adopt the tool without semantic friction (`pip install claude-…` reading as Anthropic-only) and the cross-agent policy (commands, conventions, build/test) is in one canonical place.

## Design choices (locked)

- **PyPI distribution name:** `polyreview` (operator selection). Verified PyPI-available 2026-05-29.
- **Console binary:** `polyreview` — same as distribution.
- **Python import name:** `code_review` — unchanged. Changing it breaks every internal import for zero benefit; PEP-423 + the python-dateutil precedent endorse the asymmetry.
- **Skill bundle path:** `.claude/skills/code-review/SKILL.md` — unchanged. Read by all major agents per the Agent Skills standard.
- **Skill folder name** (`code-review` inside `skills/`): unchanged. Names the capability, not the vendor or package.
- **AGENTS.md:** new file at `/Users/jiri/Code/2026/agentic-skills/code-review/AGENTS.md`. Carries the canonical cross-agent policy (commands, conventions, file layouts, autonomy rules).
- **CLAUDE.md:** shrunk to a one-line redirect (`See AGENTS.md.`). Claude Code reads it as-is.
- **Redirect meta-package:** publish `claude-code-review` 0.x.y depending only on `polyreview`. **Not a task in this story** — it depends on `polyreview` first being published to PyPI, which is operator-side off-repo work. Captured as a deferred follow-up in the runbook.
- **Cache paths** (`.claude/skills/code-review/cache/...` hardcoded in 3 adapters): also vendor-coupled but orthogonal. **Out of scope** for this story — those land in the existing `s0-t6-cache-path-unification` carryover.

### s3 execution amendments (2026-05-29, on "run s3")

- **Tag prefix `code-review-v*` kept unchanged.** The release-tag stream names the capability, not the vendor — same reasoning as keeping the `code-review/` folder and skill-folder names. Package `polyreview` is released under `code-review-v*` tags. Recorded in ADR-0014 (s3-t0) so the asymmetry is auditable, not accidental. Operator may veto in favour of renaming the prefix.
- **`.github/workflows/release.yml` folded into s3-t1.** The story's original task list omitted it, but the binary rename forces two edits there: the `test-dist` smoke step (`claude-code-review --capabilities` → `polyreview --capabilities`, else the job fails on the renamed binary) and the workflow `name:`. The tag trigger + validation regex stay (see above).

## Acceptance criteria

### Scenario: PyPI distribution renamed

- **Given** the repo after this story
- **When** `pyproject.toml` is parsed
- **Then** `[project] name == "polyreview"` (was `claude-code-review`).
- **And** `[project.scripts]` declares exactly `polyreview = "code_review.cli:app"` (binary renamed; entry-point target unchanged).
- **And** `code_review.__version__` reads `importlib.metadata.version("polyreview")` (the dist-name lookup tracks the rename).
- **And** the wheel built from this `pyproject.toml` installs as `polyreview-0.1.0-py3-none-any.whl` and exposes the binary at `<venv>/bin/polyreview`.

### Scenario: Console binary renamed, source-checkout fallback preserved

- **Given** the installed package
- **When** the operator runs `polyreview --capabilities`
- **Then** the output is valid JSON identical to the pre-rename `claude-code-review --capabilities`.
- **And** `python -m code_review.cli --capabilities` continues to work in a source checkout (developer-mode fallback unchanged).

### Scenario: Documentation reflects the new name

- **Given** the user-facing docs after this story
- **When** `README.md`, `.claude/skills/code-review/SKILL.md`, and `sdlc/docs/runbooks/release.md` are read
- **Then** every install/invocation example uses `polyreview …` (no `claude-code-review` references except in the migration note named below).
- **And** README's title is `# polyreview`.
- **And** the SKILL.md "Developer note" continues to mention `python -m code_review.cli` as the source-checkout fallback.

### Scenario: Migration note explains the rename

- **Given** `README.md` after this story
- **When** the Status section is read
- **Then** a one-paragraph migration note names the previous PyPI distribution (`claude-code-review`), states it's superseded by `polyreview`, and explains the rationale (multi-agent target).
- **And** the same note appears in `sdlc/docs/runbooks/release.md` under a new "Rename history" subsection or in CHANGELOG.md when that lands.

### Scenario: AGENTS.md exists and is canonical

- **Given** the repo after this story
- **When** `AGENTS.md` is read from the repo root (`code-review/AGENTS.md`)
- **Then** it carries the canonical cross-agent policy and links to:
  - `sdlc/SDLC.md` (the SDLC verb cycle)
  - `.claude/skills/code-review/SKILL.md` (the skill bundle, read by all agents)
  - `sdlc/docs/architecture/stack-pins.md` (pinning policy + invocation conventions per ADR-0003/ADR-0013)
- **And** AGENTS.md follows the [agents.md](https://agents.md/) format: H1 title, short summary, sections for commands / conventions / sub-projects.
- **And** AGENTS.md is read-only in spirit (claims, not just commands) — matches the existing CLAUDE.md positioning.

### Scenario: CLAUDE.md becomes a redirect

- **Given** `CLAUDE.md` after this story
- **When** read by Claude Code
- **Then** the file contains a one-line `See AGENTS.md.` redirect (plus optionally a SDLC pointer for backward compatibility with the v6.6 SDLC.md bootstrap that writes a CLAUDE.md line).
- **And** no policy content is duplicated between CLAUDE.md and AGENTS.md.

### Scenario: ADR-0014 documents the multi-agent rename strategy

- **Given** the repo after this story
- **When** `sdlc/work/active/adr-0014-multi-agent-rename.md` (or `sdlc/docs/decisions/` at story close) is read
- **Then** it records: the rename from `claude-code-review` to `polyreview`, the rationale (multi-agent neutrality, Ruff/Semgrep family naming, PEP-423 dist-vs-import asymmetry), the decision to keep the Python import name + skill bundle path + folder name unchanged, the Agent Skills standard adoption finding (`.claude/skills/` read by Copilot/Cursor/Codex/etc.), the AGENTS.md decision, and the deferred-follow-up commitment to publish a `claude-code-review` redirect meta-package concurrently with the first `polyreview` release.

## Test specification

- **`tests/test_pyproject_metadata.py`** (extend) — assert `_project()["name"] == "polyreview"`; assert `_project()["scripts"] == {"polyreview": "code_review.cli:app"}`. Replace the existing `claude-code-review` assertions wholesale.
- **`tests/test_version_source.py`** (extend) — change the metadata lookup target from `"claude-code-review"` to `"polyreview"`. Add `test_version_lookup_uses_new_distribution_name` asserting `code_review/__init__.py` calls `importlib.metadata.version("polyreview")`.
- **`tests/test_console_script_install.py`** (extend) — install the wheel, invoke `<venv>/bin/polyreview --capabilities`, assert JSON validity.
- **`tests/test_skill_md_invocation.py`** (extend) — every example invocation in SKILL.md leads with `polyreview` (the existing `claude-code-review` assertion replaced).
- **New: `tests/test_agents_md_exists.py`** — assert `AGENTS.md` exists at repo root, contains a top-level `# `, and references both `sdlc/SDLC.md` and `.claude/skills/code-review/SKILL.md` (cross-link sanity).
- **New: `tests/test_claude_md_is_redirect.py`** — assert `CLAUDE.md` is ≤5 lines and contains `AGENTS.md` (the redirect target). Catches drift back toward duplicated policy.
- **Regression**: existing 326-test green bar continues; `ruff` + `mypy` clean.

## Out of scope

- **Cache-path unification** (`.claude/skills/code-review/cache/...` hardcoded in 3 adapter modules). Existing carryover task `s0-t6-cache-path-unification` covers this. The vendor-coupled cache path doesn't block the rename, but it does block a clean "Copilot-only" install layout. Worth tackling next.
- **Publishing the `claude-code-review` redirect meta-package.** Captured as a deferred-follow-up in the release runbook + ADR-0014. Depends on `polyreview` first being published.
- **MCP wrapper** (`polyreview[mcp]` extra exposing a `polyreview-mcp` entry point). Future story candidate; the Semgrep plugin model.
- **Renaming the monorepo subdirectory** `code-review/` → anything else. The folder names a capability; renaming would break every SDLC artefact path and CI workflow path filter. Leave unchanged.
- **Renaming the skill folder** `.claude/skills/code-review/`. Same reasoning; Agent Skills spec only requires `frontmatter.name == directory_name`, not skill-name == package-name.
- **The agentic-skills root README** still missing the `code-review` row. Pre-existing L1 cleanup item from the s2 audit; separate concern.

## Open questions / risks

- **First-release timing.** The rename should land BEFORE the first real PyPI release per `sdlc/docs/runbooks/release.md` (otherwise we publish under the wrong name and rename later). The first release is blocked on operator-side Trusted Publisher setup. Order: (a) merge s3, (b) operator configures Trusted Publishers on `pypi.org` for `polyreview` + on `test.pypi.org` for `polyreview`, (c) cut the first tag.
- **Trusted Publisher binding.** ADR-0012 documented the binding under `claude-code-review`. After the rename, the binding becomes `polyreview` on PyPI / TestPyPI. The runbook needs updating to match. Captured in s3-t1 (rename sweep includes runbook).
- **Migration drift detection.** The existing `test_console_script_install` test asserts on the installed binary name. If the rename misses any artifact and that test still passes locally, CI catches it via the same path. No additional guard needed beyond the test extensions named above.
- **The s0-t6 cache-path coupling is technically a regression risk for installs under non-Claude agents** (a Copilot user would have analyzers writing to `.claude/skills/...`, which is correctly named-for-Claude). Mitigation: not in this story; addressed in s0-t6.

## Tasks

- `s3-t0-adr-0014-multi-agent-rename` — file ADR-0014 documenting the rename, the multi-agent target, AGENTS.md decision, and the redirect-meta-package deferred follow-up. No code change.
- `s3-t1-rename-pypi-and-binary-and-docs` — atomic rename: `pyproject.toml` name + scripts; `code_review/__init__.py` metadata lookup; `README.md` (all 8 sites + new migration note); `SKILL.md` (7 sites + the layout-doc parenthetical); `sdlc/docs/runbooks/release.md` (Trusted Publisher binding name; rename history); ADR-0012 (cross-reference update). Tests updated in the same commit.
- `s3-t2-agents-md-and-claude-md-redirect` — author `AGENTS.md` at repo root; shrink `CLAUDE.md` to redirect. Two new structural tests.
