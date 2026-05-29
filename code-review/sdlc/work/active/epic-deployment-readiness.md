---
id: epic-deployment-readiness
kind: epic
project: code-review
status: active
children:
  - s0-deployment-layout-fixup
  - s1-package-publication
  - s2-packaging-hardening
created: 2026-05-28
updated: 2026-05-29
tags: [deployment, packaging, release, pypi, importlib-resources]
---

# Epic: Deployment Readiness

Make `code-review` actually redistributable — a clean install under `<host>/.claude/skills/code-review/`, working wheels with all bundled data, a layout-agnostic config lookup, and one-command install from PyPI via the common Python installers (`pip`, `pipx`, `uv tool`).

## Why this is an epic, not a single story

The work splits cleanly along two axes:

- **s0 — deployment layout.** Make the package work *correctly* in every reasonable layout: developer sibling-layout (current repo), nested layout (`<host>/.claude/skills/code-review/code_review/`), wheel-installed layout (`code_review/` under site-packages). Today three things break this: `_SKILL_DIR` in `cli.py:24` hard-codes the sibling-layout path arithmetic; `pyproject.toml` doesn't declare the bundled JSON files as package data; vestigial empty `schemas/` and `agents/` directories sit in `.claude/skills/code-review/` from the original architecture sketch.

- **s1 — package publication.** Make the package *findable* from a registry. Publish to PyPI on tag-push via GitHub Actions, with TestPyPI for pre-release staging, semver with manual bumps, and a release runbook. Depends on s0 (the wheel must be complete + buildable before there's anything worth publishing).

Together they answer: "how do I install `code-review` into a new project?"

## Hypothesis (not a bet — a maintenance commitment)

Unlike `epic-reviewer-subagent`, this epic is not a hypothesis-test. The deliverables are well-defined plumbing: wheels build cleanly, configs resolve via documented lookup rules, releases publish via tag-push automation. The "did we build the right thing" question is settled by AC pass/fail, not by validation measurement.

## What's in scope

- `importlib.resources`-based loading for `capabilities.json` and `schemas/*.json` (replacing the `Path(__file__).parent` machinery).
- `code-review.toml` lookup via CWD-relative path with `--config <path>` override.
- `pyproject.toml` package-data declarations so `uv build` ships the JSON files.
- Production-layout smoke test exercising the nested layout end-to-end.
- Cleanup of vestigial empty directories.
- Bundled `code-review.toml.example` shipped with the skill, documented in SKILL.md.
- ADR-0007 (deferred decision) updated to "decided"; new ADR-0012 documenting PyPI publication.
- README.md at repo root (required by SDLC rule #17 at epic close; load-bearing for PyPI rendering).
- GitHub Actions release workflow + release runbook.

## What's intentionally not in scope

- API stability guarantees — the package stays at `0.x.y` (alpha) for this epic; semver-strict promises wait for 1.0.
- Conda / Homebrew / system-package-manager distribution.
- Wildcards on package selection: runtime-dep pinning policy per ADR-0013 (lower-bound only, anchored at locked minor); dev-dep policy per ADR-0003 §1 (exact pins, unchanged).
- Supply-chain audit automation — rule #26 remains N/A for this project; a future ADR could formalise an audit gate.
- Multi-architecture wheel builds (`code-review` is pure Python; one wheel covers all platforms).
- Telemetry on installs / downloads.

## Stories

0. **s0-deployment-layout-fixup** — Fix the layout / wheel / config-lookup issues that block any reasonable install. Prerequisite for s1.
1. **s1-package-publication** — Publish to PyPI via GitHub Actions on tag-push; semver + manual bumps; TestPyPI for staging; release runbook.
2. **s2-packaging-hardening** — Bring packaging to current PyPA best practice: LICENSE bundled in the wheel, runtime deps lower-bounded (ADR-0013), `__version__` single-sourced via `importlib.metadata`, three-job release workflow (build → test-dist → publish, OIDC scoped to publish, official PyPA action), push/PR CI workflow gating on pytest+ruff+mypy, SKILL.md leads with the installed `claude-code-review` binary, `setup.sh` BUNDLE_DIR fix.

## Future stories (anticipated but not yet planned)

- Supply-chain audit gate ADR + `make audit` target (`pip-audit` integration) — would activate SDLC rule #26 for this project.
- 1.0 graduation: stability guarantee for `--review` / `--depth` flags + `capabilities.json` schema; deprecation policy for analyzer removals.
- Optional second registry (e.g., GitHub Releases asset attachment) for users who prefer not to depend on PyPI.

The epic stays open as a stable home for those.
