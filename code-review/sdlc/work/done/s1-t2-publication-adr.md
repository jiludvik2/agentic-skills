---
id: s1-t2-publication-adr
kind: task
project: code-review
status: done
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
closed: 2026-05-28
verify: PASS (commit c2a8c68; 302 passed/6 skipped; ruff clean; pre-existing mypy conftest dup carried over)
review: CLEAN (zero findings; informational note: parent story s1-t5 ACs still mention API tokens, contradicts ADR-0012 — must refresh before s1-t5 build)
---

# s1-t2 — ADR-0012 documenting PyPI publication

## Outcome

A new ADR records the decision to publish `code-review` to PyPI via GitHub Actions on tag-push, with TestPyPI staging and semver manual bumps. Extends ADR-0001 (which currently only names the source host, not a package registry).

## Acceptance criteria

- `sdlc/work/active/adr-0012-pypi-publication.md` is created (moves to `sdlc/docs/decisions/` at story close per the SDLC's co-locate-active-work convention). Frontmatter: `kind: decision`, `status: accepted`, `parent: s1-package-publication`, `sources: [adr-0001-publication.md]`.
- Contents:
  - **Status**: Accepted.
  - **Context**: ADR-0001 locks the source-code host (GitHub monorepo) but doesn't name a Python package registry. To support `pip install claude-code-review` from any environment, a registry decision is needed.
  - **Decision**:
    - **Registry**: PyPI (https://pypi.org/). Justification: native `pip`/`pipx`/`uv tool` support; no extra index-URL flags for end users; standard for open-source Python.
    - **Distribution name**: `claude-code-review`. The bare `code-review` is already taken on PyPI; `claude-code-review` ties the package to its host platform (Claude Code skills) and remains discoverable.
    - **Console-script binary**: `claude-code-review` (matches the distribution name; avoids `$PATH` collisions with any existing `code-review` console-script). Python import name stays `code_review`.
    - **Pre-release staging**: TestPyPI (https://test.pypi.org/) for release-candidate verification.
    - **Versioning**: Semver. `0.x.y` while pre-1.0 (no API stability guarantee); `1.0.0` once `--review`/`--depth` flags and `capabilities.json` schema are stable.
    - **Release mechanism**: GitHub Actions on tag push (`code-review-v*` → PyPI, `code-review-v*-rc*` → TestPyPI), authenticated via **PyPI Trusted Publishers (OIDC)** — no long-lived API tokens. The publish job declares `permissions: id-token: write` and `uv publish` exchanges the GitHub OIDC identity for a short-lived upload token at runtime. The `code-review-` tag prefix isolates this subproject's releases from sibling subprojects sharing the monorepo's `.github/workflows/`.
    - **Version-bump discipline**: `pyproject.toml` version + git tag created in the same commit. No automation; manual bumps avoid surprise releases.
  - **Consequences**:
    - Anyone can `pip install claude-code-review` after the first release lands.
    - Users invoke the CLI as `claude-code-review …` rather than `code-review …`; documentation and the README must reflect this.
    - License footprint widens — PyPI rendering surfaces the README; the license (MIT per ADR-0001) is unchanged.
    - Supply-chain attack surface gains a single point of trust (PyPI itself). Mitigated by the project's existing exact-pin policy (ADR-0003) and by Trusted Publishers (no long-lived publish token can be exfiltrated from the repo).
    - First release requires one-time PyPI-side admin: create a "pending publisher" on PyPI and on TestPyPI binding the `jiludvik2/agentic-skills` repo + `release.yml` workflow file + (optionally) a `pypi` environment. Documented in the release runbook.
    - Adding a second publishable subproject to the monorepo (e.g., `intent-review`) requires a parallel `<subproject>-v*` tag prefix and a separate workflow file (with its own Trusted Publisher configuration on PyPI) or a matrixed branch in the existing one.
  - **Alternatives considered**:
    - **GitHub Packages**: rejected — no first-class Python support; install UX is verbose (`--index-url` flag); discoverability is worse.
    - **`pip install git+https://...`**: rejected — every install builds from source; tags are visible but the install URL is the canonical interface.
    - **GitHub Releases asset attachment**: rejected — install URL is verbose; users would still need to know exact wheel filenames.
    - **API tokens (`PYPI_API_TOKEN`/`TESTPYPI_API_TOKEN`) instead of Trusted Publishers**: rejected — long-lived secrets in GitHub repository settings; manual rotation discipline; broader blast radius if the GitHub repo is compromised. Trusted Publishers eliminates these costs at the price of one-time PyPI-side setup, which is acceptable given the workflow is already locked to GitHub Actions.

## Test specification

- **No automated test for ADR content** — ADRs are prose; verification is a manual read by the operator.
- **`tests/test_skill_scaffold.py`** or equivalent: confirm the ADR file lives at the expected path under `/sdlc/work/active/` (will move to `/sdlc/docs/decisions/` at story close).

## Notes

- ADR numbering: 0012 is next after 0011. Confirm `/sdlc/docs/decisions/` lists 0001–0011 before assigning.
- ADR-0001 stays as-is — it covers the source-code host; this ADR is about the package registry. They're complementary, not overlapping.
- If the operator later decides to also publish to a second registry (private index, etc.), that's a new ADR — don't try to make 0012 future-proof.
