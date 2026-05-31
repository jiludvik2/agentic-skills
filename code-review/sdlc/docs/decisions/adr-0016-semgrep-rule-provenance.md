---
id: adr-0016-semgrep-rule-provenance
kind: decision
project: code-review
status: accepted
parent: s0-t0-adr-semgrep-rule-provenance
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, s0-semgrep-rule-source.md]
created: 2026-05-29
updated: 2026-05-29
tags: [semgrep, rules, cache, security, provenance]
---

# ADR-0016: Semgrep rule provenance & resolution

## Status

Accepted. Resolves FINDINGS.md F3 (semgrep produces zero findings out of the box)
under `epic-analyzer-ga-hardening` / s0.

## Context

On a fresh install the semgrep analyzer returns no findings — it errors. Three
problems compound:

1. **No rules are shipped.** `scripts/prefetch_caches.py` is a stub
   (`_ARTIFACTS = {}`); the comment defers "Semgrep rule packs" to "s3", which
   was repurposed into the package rename and never delivered them. So
   `cache_root()/cache/semgrep/rules` is never populated.
2. **The fallback is self-contradictory.** With no local rules the adapter runs
   `--config auto` together with `--metrics off`; semgrep refuses:
   `Cannot create auto config when metrics are off`.
3. **The rules dir ignores `$POLYREVIEW_CACHE_DIR`.** `semgrep._semgrep_rules_dir()`
   anchors on `Path.cwd() / ".claude/skills/code-review/cache/semgrep/rules"`
   directly, not through `cache_root()` (ADR-0015). Producer and consumer can
   therefore diverge when the cache dir is overridden.

The adapter's local-rules path is otherwise correct: the analyzer-coverage smoke
test confirms semgrep finds the planted `eval`/`shell=True` defects once a
ruleset is present in the cache.

> **s0-t2 correction (2026-05-29).** This ADR earlier stated the
> `--x-ignore-semgrepignore-files` flag was "not recognized by the installed
> semgrep (a non-fatal warning today)." That was empirically wrong: on the
> pinned semgrep **1.161.0** the flag is recognized and **load-bearing** — it
> disables semgrep's default `.semgrepignore` patterns (which exclude `tests/`).
> Verified directly: scanning `tests/fixtures/python-with-known-issues` yields
> the planted finding *with* the flag and **zero findings without it**. Per this
> ADR's own scan-scope caveat (below), s0-t2 therefore **keeps** the flag rather
> than dropping it; the semgrep pin is the version guard.

## Decision

1. **Provenance: vendored-in-bundle** (operator-confirmed, 2026-05-29). A curated
   security ruleset lives in the skill bundle at
   `.claude/skills/code-review/semgrep-rules/`; `setup.sh` copies it into
   `cache_root()/cache/semgrep/rules/`. Chosen over prefetch-download from the
   semgrep registry to keep `setup.sh` offline, deterministic, and free of
   registry-download license ambiguity. The maintenance commitment is ours:
   refreshing the vendored rules is a deliberate, reviewable change.

2. **Ruleset scope & license.** Security rules for **Python and JS/TS** (JS/TS
   covered as of s3, 2026-05-31 — see amendment below). The vendored
   rules must carry a license compatible with the `stack-pins.md` floor
   (LGPL-2.1 acceptable via subprocess invocation; **no AGPL**). The rule source
   and its version/commit are recorded alongside the vendored files. Two rule
   dirs exist today but are **fixtures, not the canonical vendored set**:
   `tests/fixtures/semgrep-rules/` (unit-test fixture) and
   `sdlc/docs/qa/analyzer-coverage/semgrep-rules/` (smoke-test fixture). s0-t1
   creates the canonical set under `.claude/skills/code-review/semgrep-rules/`,
   seeded from these, and records its provenance; the fixtures stay independent.

   > **Amendment (2026-05-30, operator-approved).** The s0 story-level review
   > flagged that the shipped `security.yaml` carries Python-only rules while this
   > decision read "Python and JS/TS". Operator decision: **amend the scope to
   > Python-first**; JS/TS security rules are a tracked follow-up, not an s0
   > deliverable. Rationale: keep s0 (F3) closed on the Python coverage that is
   > built and proven, rather than reopening it to author unvalidated JS/TS rules.
   > A future ADR/story adds JS/TS rules when there is demand; the vendored-bundle
   > provisioning path (s0-t1/t2) already supports them with no further plumbing.

   > **Amendment (2026-05-31, s3).** The JS/TS follow-up tracked since the
   > 2026-05-30 amendment is delivered: `security-js.yaml` (MIT, hand-authored)
   > adds `js-eval` (CWE-95, ERROR) and `js-innerhtml-xss` (CWE-79, WARNING) for
   > `[javascript, typescript]`. Provisioning unchanged — `provision_semgrep_rules()`
   > globs `*.y*ml` and copies all files idempotently, so the new file required no
   > plumbing change (the epic's architecture-validation criterion). Validated
   > end-to-end via `test_semgrep_js_rules_fire_on_js_fixture` (integration).

3. **Resolution precedence**, with the anchor corrected to `cache_root()`:
   explicit `config["semgrep_rules"]` override → `cache_root()/cache/semgrep/rules`
   → missing-cache behavior (see #4). `_semgrep_rules_dir()` resolves through
   `cache_root()` so it honors `$POLYREVIEW_CACHE_DIR` like every other cache
   consumer (ADR-0015).

4. **Missing-cache behavior: fail loudly.** When neither an override nor a
   populated cache is found, the adapter returns `status=error` with an
   actionable message naming `scripts/setup.sh`. The `--config auto` +
   `--metrics off` combination is removed entirely — `auto` is not a supported
   fallback for this tool. (Rationale: a silent empty success on a security
   analyzer is worse than a loud, fixable error.)

5. **CLI exposure of `semgrep_rules`: yes.** `load_config` parses an optional
   `semgrep_rules` path from `code-review.toml` and threads it into
   `request.config`, closing the gap between the adapter (which already reads it,
   and the integration test which already supplies it) and the CLI (which never
   populated it).

Also: the unsupported `--x-ignore-semgrepignore-files` flag is dropped (or
version-guarded to semgrep versions that accept it) in s0-t2. Note that flag
existed to bypass semgrep's default ignore of `tests/`; dropping it reverts to
that default, so s0-t2 must confirm scan-scope coverage (or version-guard rather
than remove) so test-directory findings aren't silently lost.

## Consequences

- A clean `setup.sh` makes `polyreview --review security` return findings with no
  manual provisioning; the analyzer-coverage smoke harness drops its
  `_provision_semgrep_rules()` workaround (s0-t3).
- Rule freshness is a maintenance task, not automatic — acceptable for a
  deterministic, offline-first analyzer; revisit if rule staleness becomes a
  problem (a future ADR could add an opt-in prefetch path).
- Supersedes the stale "Semgrep rule packs in s3" deferral, which actually lives
  in `scripts/setup.sh:88` (the prefetch step comment) and
  `scripts/prefetch_caches.py:4-5,32` (the stub docstring + empty `_ARTIFACTS`) —
  **not** in `stack-pins.md`. s0-t1 updates those two locations.
