---
id: adr-0013-runtime-vs-dev-dependency-pinning
kind: decision
project: code-review
status: accepted
parent: s2-packaging-hardening
sources: [adr-0003-exact-version-pinning-and-pip-fallback.md, adr-0012-pypi-publication.md, s2-packaging-hardening.md]
supersedes-partial: adr-0003-exact-version-pinning-and-pip-fallback.md
created: 2026-05-29
updated: 2026-05-29
tags: [dependencies, governance, supply-chain, pypi, packaging]
---

# ADR-0013: Split dependency-pinning policy — runtime lower-bounded, dev exact-pinned

## Status

Accepted. Partially supersedes ADR-0003 §Decision item 1 ("Pin every tool version exactly") for **runtime dependencies only**. ADR-0003's other three decisions (pip-install fallback, ruff via CLI, no uv-specific pyproject features) remain in force unchanged.

## Context

ADR-0003 (May 2026) mandated exact (`==`) version pins on every dependency as a supply-chain mitigation, written against the Astral/OpenAI governance-risk backdrop. At that time the package was internal — installed via `pip install -e .` from a checkout, never resolved alongside a consumer's existing environment.

ADR-0012 (May 2026, s1-t2) changed that. `claude-code-review` is now a PyPI-published CLI installed by third parties via `pip install claude-code-review`, `pipx install claude-code-review`, or `uv tool install claude-code-review`. Exact pins on the eight runtime dependencies (`typer==0.18.0`, `jsonschema==4.26.0`, `bandit==1.7.10`, `radon==6.0.1`, `vulture==2.13`, `pydeps==1.12.20`, `cohesion==1.1.0`, `schemathesis==4.0.10`) prevent pip from resolving alongside any other package that needs a different version of those libraries — silently breaking the `pip install` path for any consumer who has a venv with prior installs.

The PyPA packaging guide (2024-2026) recommends: **for distributed packages, set a lower bound at the minimum supported minor; add upper bounds only when there is evidence of a specific incompatibility.** Reproducibility for *developers* is the lockfile's job (`uv.lock`), not the spec's. This separation is the de-facto standard for Python CLI tools published in 2025+.

ADR-0003's governance intent — "version bumps are deliberate, reviewed events" — remains valuable but is enforced at a different layer for runtime deps: the lockfile pins exact versions, `uv sync --frozen` enforces them in CI and local dev, and the relaxed `pyproject.toml` bound exists only for downstream consumers. The "deliberate, reviewed" event becomes the `uv.lock` change (and its associated `stack-pins.md` reconciliation), not the `pyproject.toml` change.

## Decision

1. **Runtime dependencies (`[project.dependencies]`): lower-bound only, anchored at the currently-locked minor.** Form: `name>=X.Y`. No upper bound by default.

2. **Justified upper bounds are permitted** on runtime deps when there is evidence of a specific incompatibility with a future major (e.g., a recent breaking-change release). Format: `name>=X.Y,<Z  # reason`. The inline `#` comment is mandatory.

3. **Dev dependencies (`[dependency-groups] dev`): stay exact-pinned (`==X.Y.Z`).** Dev tooling (pytest, mypy, ruff, fastapi, uvicorn) is never shipped to consumers; reproducible CI matters more than transitive flexibility. ADR-0003's exact-pin policy applies unchanged here.

4. **Subprocess-only tools** (semgrep, gitleaks, trivy, eslint, etc.) remain governed by `scripts/setup.sh` and `package-lock.json`; outside the scope of this ADR.

5. **`uv.lock` continues to pin exact versions** for runtime AND dev deps. Developer reproducibility is unchanged. `uv sync --frozen` is the canonical install command for the dev environment.

6. **The schemathesis exception** (current): `schemathesis>=4.0,<5  # 3→4 was a breaking-change major; pin to current major until 5.x is tested`. This is the only currently-justified upper bound. Future exceptions follow the same `# reason` convention.

## Consequences

- `pip install claude-code-review` succeeds in environments that already have any reasonable version of the runtime deps. The known pip-fallback path (ADR-0003 item 2) is preserved AND extended to the consumer side.

- Developer experience is unchanged: `uv sync --frozen` installs the locked versions deterministically. The lockfile becomes the single source of truth for what the project *was tested against*; the spec is the contract for what the project *will work with*.

- Governance still bites. A version bump in `uv.lock` (the substantive change) lands as a reviewed, committed event, with `stack-pins.md` reconciled in the same commit per SDLC rule #1b. The `pyproject.toml` minor-anchor changes only when we drop support for an older minor — also a reviewed event.

- The "deliberate, reviewed" framing from ADR-0003 still applies; it just attaches to lockfile bumps + `stack-pins.md` reconciliation, not to `pyproject.toml` edits.

- Supply-chain risk surface is unchanged in practice. A compromised upstream affects the developer first (lockfile pin) and only reaches consumers if they install AFTER we ship a release that bumps the locked floor. Catching upstream compromise is the lockfile's job, not the spec's.

- `stack-pins.md` is updated to reflect the split: the runtime-deps table shows lockfile-pinned exact versions (the *what was tested*) with the spec floors documented alongside.

## Alternatives considered

- **Keep ADR-0003 unchanged, accept pip-install conflicts as a known trade-off.** Rejected: the s2 story's audit identified pin-induced resolution conflicts as a Hard finding blocking the first public release. The trade-off is no longer acceptable post-PyPI-publication.

- **Move dev deps to lower-bound too.** Rejected: no operator benefit — only the dev/CI side runs `uv sync --frozen`, and that step doesn't care about lower vs exact since it ignores the spec in favour of the lock. Exact pins on dev deps cost nothing and signal intent.

- **Reduce scope to schemathesis only (since 3→4 was the documented breakage).** Rejected: the resolution-conflict problem is structural and affects all eight deps, not just schemathesis. A single-dep fix would leave the other seven blocking pip-installs.

## Cross-references

- ADR-0003 §Decision item 1 — superseded for runtime deps; other items unchanged.
- ADR-0012 §Decision — PyPI publication, the context that made this split necessary.
- `stack-pins.md` §Python dependencies — updated in the same commit to show spec floor + lockfile pin together.
- s2-packaging-hardening §Design choices — the story-level locked decision this ADR formalises.
