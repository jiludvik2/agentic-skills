---
id: s0-t6-cache-path-unification
kind: task
project: code-review
status: done
parent: s0-deployment-layout-fixup
sources: [s0-t2-cwd-relative-toml.md]
created: 2026-05-28
updated: 2026-05-29
tags: [deployment, cache, trivy, npm, architecture]
notes: |
  Closed 2026-05-29. Single resolver code_review.paths.cache_root()
  ($POLYREVIEW_CACHE_DIR else CWD/.claude/skills/code-review) consumed by producer
  (prefetch_caches.py + setup.sh) and consumers (trivy/js_base). ADR-0015 records
  the CWD-anchor + env-override decision (operator-selected). Verify PASS; per-task
  Review MINOR-ONLY. Resolved in-task: shell-quoting robustness (env-var path pass),
  cache-anchor visibility note in setup.sh, stale find_host_root comment, and a
  wheel-no-producer layout-agnostic clean-error test. Left per reviewer: the dual
  sys.path-bootstrap Nit (acceptable). Documented residual: in dev-sibling layout,
  producer/consumer alignment assumes the CLI runs from the same anchor setup.sh
  chose (surfaced via the new "cache anchor:" setup.sh note). 351 passed.

# s0-t6 — Producer/consumer cache-path unification

## Outcome

The path where `scripts/setup.sh` + `scripts/prefetch_caches.py` *write*
operator-runtime caches (trivy DB, node_modules) is the same path that
`code_review/adapters/trivy.py` and `code_review/adapters/js_base.py` *read*.
A single resolver — consumed by both producer and consumer — owns the cache
location, eliminating the silent divergence that exists today.

## Background

Pre-dating s0-t2, the producer and consumer have used different path
conventions:

- **Producer**: `setup.sh` runs `cd "${SKILL_ROOT}" && python prefetch_caches.py`;
  `prefetch_caches.py` writes to `Path.cwd() / "cache"`; `npm ci` installs to
  `${SKILL_ROOT}/node_modules/`. `SKILL_ROOT = scripts/..` = `<repo>/code-review/`
  in dev sibling layout, or `<host>/.claude/skills/code-review/` in production
  nested layout.
- **Consumer (s0-t2 and earlier)**: `<cwd>/.claude/skills/code-review/cache/trivy-db`
  and `<cwd>/.claude/skills/code-review/node_modules`.

These align *only* in the production-nested layout with the CLI run from
`<host>/`. They diverge in dev sibling and have no producer at all in the
wheel-installed layout. The test suite patches the consumer-side helpers so
the divergence never surfaces in tests.

Story s0's AC8 ("production-layout smoke test") happens to pass because it
uses precisely the production-nested layout where the paths coincidentally
align.

## Acceptance criteria

- A single resolver (e.g., `code_review.paths.cache_root()` or similar) is
  the only source-of-truth for the cache base directory.
- `scripts/prefetch_caches.py` imports the resolver (or is given the path as
  an argument) and writes to it.
- `scripts/setup.sh` is updated if needed (it currently `cd`s to `SKILL_ROOT`
  before invoking `prefetch_caches.py`; this may become unnecessary).
- `code_review/adapters/trivy.py:_trivy_cache_dir()` and
  `code_review/adapters/js_base.py:_node_modules()` consume the same resolver.
- A test verifies producer and consumer return the same path under each of
  the three supported layouts (dev sibling, production nested, wheel-installed).
- The wheel-installed-no-producer case is documented: cache absent → clean
  error message that doesn't misleadingly tell the operator to "Run
  scripts/setup.sh" if no such script ships with the wheel.

## Test specification

- **New: `tests/test_cache_path_unification.py`** — table-driven over the
  three layouts; assert the resolver and `prefetch_caches.py`'s effective
  write path agree.
- **Regression**: `tests/test_adapters/test_trivy.py`, `test_js_base.py`,
  `test_sandbox_compatibility.py` continue to pass (they patch the resolver).

## Notes

- This task is the deferred follow-up to the Important reviewer finding
  raised against s0-t2 (filed pre-emptively rather than as a fix task because
  the issue pre-dates s0-t2 and the design decision is architectural in
  scope).
- The current dev tree has never had `setup.sh` run, so no cache directories
  exist; the divergence is latent.
- Consider an ADR for the layout-vs-cache-location decision if the design
  isn't obvious during planning.
