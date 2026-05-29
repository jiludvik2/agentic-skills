---
id: adr-0015-cache-path-unification
kind: decision
project: code-review
status: accepted
parent: s0-t6-cache-path-unification
sources: [s0-t6-cache-path-unification.md, s0-t2-cwd-relative-toml.md]
created: 2026-05-29
updated: 2026-05-29
tags: [deployment, cache, paths, trivy, node, architecture]
---

# ADR-0015: Unify the cache base path behind one CWD-anchored resolver

## Status

Accepted. Resolves the producer/consumer cache-path divergence flagged as an Important finding against s0-t2.

## Context

Operator-runtime caches (the Trivy vulnerability DB; vendored Node `node_modules`) are written by a **producer** (`scripts/setup.sh` + `scripts/prefetch_caches.py`) and read by **consumers** (`code_review/adapters/trivy.py`, `code_review/adapters/js_base.py`). The two sides used different path conventions:

- Producer: `prefetch_caches.py` wrote `Path.cwd() / "cache"` after `setup.sh` `cd`'d to `SKILL_ROOT`; `npm ci` installed into `SKILL_ROOT/node_modules`.
- Consumers: read `Path.cwd() / ".claude/skills/code-review/{cache,node_modules}"`.

These align only in the production-nested layout with the CLI run from the host root; they diverge in the dev-sibling layout and have no producer at all in the wheel-installed layout. The test suite patched the consumer helpers, so the divergence never surfaced.

The rest of the codebase is consistently **CWD-anchored**: the `code-review.toml` lookup (`cli.py`) and the `--output` sandbox guard both resolve against `Path.cwd()`.

## Decision

Introduce a single resolver in `code_review/paths.py` as the source of truth for the cache base directory, consumed by both producer and consumer:

```python
def cache_root() -> Path:
    env = os.environ.get("POLYREVIEW_CACHE_DIR")
    if env:
        return Path(env)
    return Path.cwd() / ".claude" / "skills" / "code-review"

def trivy_cache_dir() -> Path:   return cache_root() / "cache" / "trivy-db"
def node_modules_dir() -> Path:  return cache_root() / "node_modules"
```

- **Anchor: CWD**, matching the existing `code-review.toml` / `--output` convention. No new anchoring scheme to reason about.
- **Override: `$POLYREVIEW_CACHE_DIR`** — an explicit escape hatch for CI, tests, and deployments where CWD-anchoring is inconvenient. Both sides honour it, so they cannot disagree.
- `trivy.py` and `js_base.py` import the resolver; `prefetch_caches.py` writes to `cache_root()/cache` and exposes `prefetch_cache_dir()`; `setup.sh` runs the producer from the host-root anchor (nearest `.claude/` ancestor) so the nested layout aligns, and honours `$POLYREVIEW_CACHE_DIR` when set.

## Consequences

- Producer and consumer can no longer drift — they call one function. A test (`tests/test_cache_path_unification.py`) asserts the producer's write dir and the consumers' read paths resolve to one tree under both anchoring modes.
- **Wheel-installed-no-producer layout:** no `setup.sh` ships, so caches are simply absent; the adapters now emit a layout-agnostic "cache absent" error that points at `setup.sh` *or* `$POLYREVIEW_CACHE_DIR` rather than unconditionally telling the operator to run a script that isn't present.
- The pre-existing `SkillPaths` class (skill-root-anchored, used only by its own test) is left untouched; it is not wired into production and is orthogonal to this resolver.

## Alternatives considered

- **Skill-bundle-anchored resolver** (discover the installed `.claude/skills/code-review/` that ships `SKILL.md`, anchor both sides there). More robust across layouts in principle, but needs non-trivial bundle-discovery logic, has no writable bundle dir / no producer in the wheel layout, and diverges from the established CWD convention. Rejected for complexity.
- **Status quo + patched tests** — rejected; the divergence is a latent deployment bug, not a test artefact.

## Cross-references

- s0-t6-cache-path-unification (the task).
- s0-t2-cwd-relative-toml (origin of the Important finding; the `--output`/toml CWD convention this aligns with).
