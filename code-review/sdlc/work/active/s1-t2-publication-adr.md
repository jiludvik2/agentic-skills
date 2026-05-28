---
id: s1-t2-publication-adr
kind: task
project: code-review
status: active
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
---

# s1-t2 — ADR-0012 documenting PyPI publication

## Outcome

A new ADR records the decision to publish `code-review` to PyPI via GitHub Actions on tag-push, with TestPyPI staging and semver manual bumps. Extends ADR-0001 (which currently only names the source host, not a package registry).

## Acceptance criteria

- `sdlc/work/active/adr-0012-pypi-publication.md` is created (moves to `sdlc/docs/decisions/` at story close per the SDLC's co-locate-active-work convention). Frontmatter: `kind: decision`, `status: accepted`, `parent: s1-package-publication`, `sources: [adr-0001-publication.md]`.
- Contents:
  - **Status**: Accepted.
  - **Context**: ADR-0001 locks the source-code host (GitHub monorepo) but doesn't name a Python package registry. To support `pip install code-review` from any environment, a registry decision is needed.
  - **Decision**:
    - **Registry**: PyPI (https://pypi.org/). Justification: native `pip`/`pipx`/`uv tool` support; no extra index-URL flags for end users; standard for open-source Python.
    - **Pre-release staging**: TestPyPI (https://test.pypi.org/) for release-candidate verification.
    - **Versioning**: Semver. `0.x.y` while pre-1.0 (no API stability guarantee); `1.0.0` once `--review`/`--depth` flags and `capabilities.json` schema are stable.
    - **Release mechanism**: GitHub Actions on tag push (`v*` → PyPI, `v*-rc*` → TestPyPI), using `PYPI_API_TOKEN` and `TESTPYPI_API_TOKEN` repository secrets.
    - **Version-bump discipline**: `pyproject.toml` version + git tag created in the same commit. No automation; manual bumps avoid surprise releases.
  - **Consequences**:
    - Anyone can `pip install code-review` after the first release lands.
    - The package name `code-review` must be available on PyPI; if not, fall back to `<alt-name>` (operator picks; ADR amended if rename happens).
    - License footprint widens — PyPI rendering surfaces the README; the license (MIT per ADR-0001) is unchanged.
    - Supply-chain attack surface gains a single point of trust (PyPI itself). Mitigated by the project's existing exact-pin policy (ADR-0003).
  - **Alternatives considered**:
    - **GitHub Packages**: rejected — no first-class Python support; install UX is verbose (`--index-url` flag); discoverability is worse.
    - **`pip install git+https://...`**: rejected — every install builds from source; tags are visible but the install URL is the canonical interface.
    - **GitHub Releases asset attachment**: rejected — install URL is verbose; users would still need to know exact wheel filenames.

## Test specification

- **No automated test for ADR content** — ADRs are prose; verification is a manual read by the operator.
- **`tests/test_skill_scaffold.py`** or equivalent: confirm the ADR file lives at the expected path under `/sdlc/work/active/` (will move to `/sdlc/docs/decisions/` at story close).

## Notes

- ADR numbering: 0012 is next after 0011. Confirm `/sdlc/docs/decisions/` lists 0001–0011 before assigning.
- ADR-0001 stays as-is — it covers the source-code host; this ADR is about the package registry. They're complementary, not overlapping.
- If the operator later decides to also publish to a second registry (private index, etc.), that's a new ADR — don't try to make 0012 future-proof.
