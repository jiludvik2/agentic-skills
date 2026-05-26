---
id: s1-t3-fix1-defer-agent-install-and-harden-prefetch
kind: task
project: code-review
status: done
parent: s1-reviewer-skill-and-capabilities
sources: [s1-t3-reviewer]
created: 2026-05-26
updated: 2026-05-26
---

# s1-t3-fix1 — Defer reviewer.md install to t4; harden prefetch

## Context

The s1-t3 review raised a Critical (reviewer.md install step silently skips — source
path/topology mismatch) and an Important (host-root `cd ../../.. 2>/dev/null` resolution is
fragile and, once activated, could `cp` into the wrong `.claude/agents/`). Root cause: the
install step was added to setup.sh in t3 before the source reviewer.md (t4) and a robust
host-root resolution existed. Rather than ship fragile, guarded-off path math, the install
step is removed from t3 and moved wholesale to s1-t4, which owns the reviewer.md content,
its bundled source location, and its dispatch — so install path resolution gets built and
tested alongside the file it copies.

## Acceptance Criteria

- `scripts/setup.sh` no longer contains the reviewer.md copy / host-root (`../../..`) block.
  Steps 1–3 (python deps, guarded node deps, prefetch) remain; a comment records that the
  Reviewer sub-agent install is added in s1-t4 with verified host-root resolution.
- `scripts/prefetch_caches.py` self-heals a corrupt/unreadable `manifest.json`: a parse
  failure is treated as "no manifest" (forces a clean rewrite) instead of crashing with a
  traceback.
- The `prefetch_caches.py` docstring no longer claims on-disk content-hash verification;
  it accurately describes manifest-id→hash addressing (s3 must verify on-disk bytes).
- All existing s1-t3 tests stay GREEN; `bash -n scripts/setup.sh` still passes.

## Test specification

Additions to `tests/test_setup_script.py`:

- `test_prefetch_recovers_from_corrupt_manifest` — create `cache/manifest.json` with invalid
  JSON in a tmp CWD; run `prefetch_caches.py`; assert exit 0 and the manifest is now valid JSON.
- `test_setup_script_has_no_host_root_traversal` — assert `scripts/setup.sh` text contains
  neither `../../..` nor `2>/dev/null` (the removed fragile resolution), guarding against
  regression.

## Notes

- Reviewer "Critical" (source path) is resolved by removal: the install step and its source
  convention are now wholly t4's. No silent-skip step remains in t3.
- s1-t4 scope expands to include the setup.sh install step with walk-up-to-`.claude/`
  host-root resolution, fail-loud on no project root, and a test that exercises the copy
  (byte-identical across runs).
