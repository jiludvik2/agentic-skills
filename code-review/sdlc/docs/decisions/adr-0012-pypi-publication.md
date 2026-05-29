---
id: adr-0012-pypi-publication
kind: decision
project: code-review
status: accepted
parent: s1-package-publication
sources: [adr-0001-publication.md]
created: 2026-05-28
updated: 2026-05-28
---

# ADR-0012 — Publish `claude-code-review` to PyPI via GitHub Actions on tag push

## Status

Accepted. **Distribution name superseded by ADR-0014 (2026-05-29):** the distribution and console binary were renamed `claude-code-review` → `polyreview`. References to `claude-code-review` below are retained as the historical record; the publication mechanism (Trusted Publishers / OIDC, three-job `release.yml`, `code-review-v*` tag routing) is unchanged — only the bound distribution name moved.

## Context

ADR-0001 locks the source-code host (GitHub monorepo) but does not name a Python package registry. To support `pip install claude-code-review` from any environment, a registry decision is needed.

## Decision

- **Registry**: [PyPI](https://pypi.org/). Native `pip` / `pipx` / `uv tool` support; no extra `--index-url` flag for end users; standard for open-source Python.
- **Distribution name**: `claude-code-review`. The bare `code-review` is already taken on PyPI; `claude-code-review` ties the package to its host platform (Claude Code skills) and stays discoverable.
- **Console-script binary**: `claude-code-review` (matches the distribution name; avoids `$PATH` collisions with any existing `code-review` console-script). Python import name stays `code_review`.
- **Pre-release staging**: [TestPyPI](https://test.pypi.org/) for release-candidate verification.
- **Versioning**: Semver. `0.x.y` while pre-1.0 (no API stability guarantee); `1.0.0` once `--review` / `--depth` flags and `capabilities.json` schema are stable.
- **Release mechanism**: GitHub Actions on tag push.
  - `code-review-v*` → PyPI.
  - `code-review-v*-rc*` → TestPyPI.
  - Authenticated via **PyPI Trusted Publishers (OIDC)** — no long-lived API tokens. The publish job declares `permissions: id-token: write`; `uv publish` exchanges the GitHub OIDC identity for a short-lived upload token at runtime.
  - The `code-review-` tag prefix isolates this subproject's releases from sibling subprojects sharing the monorepo's `.github/workflows/`.
- **Version-bump discipline**: `pyproject.toml` `version` and the git tag are created in the same commit. No automation; manual bumps avoid surprise releases.

## Consequences

- Anyone can `pip install claude-code-review` after the first release lands.
- Users invoke the CLI as `claude-code-review …` rather than `code-review …`; documentation and the README must reflect this. (README already does — see `s1-t1`.)
- License footprint widens — PyPI rendering surfaces the README; the license (MIT per ADR-0001) is unchanged.
- Supply-chain attack surface gains a single point of trust (PyPI itself). Mitigated by the project's existing exact-pin policy (ADR-0003) and by Trusted Publishers (no long-lived publish token can be exfiltrated from the repo).
- First release requires one-time PyPI-side admin: create a "pending publisher" on PyPI and on TestPyPI binding the `jiludvik2/agentic-skills` repo, the `release.yml` workflow filename, and (optionally) a `pypi` environment. Documented in the release runbook (`s1-t5`).
- Adding a second publishable subproject to the monorepo (e.g., `intent-review`) requires a parallel `<subproject>-v*` tag prefix and a separate workflow file (with its own Trusted Publisher configuration on PyPI) or a matrixed branch in the existing one.

## Alternatives considered

- **GitHub Packages** — rejected. No first-class Python support; install UX is verbose (`--index-url` flag); discoverability is worse.
- **`pip install git+https://…`** — rejected. Every install builds from source; tags are visible but the install URL is not the canonical interface.
- **GitHub Releases asset attachment** — rejected. Install URL is verbose; users would still need to know exact wheel filenames.
- **API tokens (`PYPI_API_TOKEN` / `TESTPYPI_API_TOKEN`) instead of Trusted Publishers** — rejected. Long-lived secrets in GitHub repository settings; manual rotation discipline; broader blast radius if the GitHub repo is compromised. Trusted Publishers eliminates these costs at the price of one-time PyPI-side setup, which is acceptable given the workflow is already locked to GitHub Actions.
