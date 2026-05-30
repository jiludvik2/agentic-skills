---
id: s0-t2-adapter-resolution-and-fallback
kind: task
project: code-review
status: done
parent: s0-semgrep-rule-source
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [semgrep, adapter, cache-root, fallback]
notes: |
  Review (MINOR-ONLY). Findings:
  - [APPLIED] Minor: a non-existent `semgrep_rules` override silently fell
    through to the cache; now fails loud naming the override path
    (semgrep.py + test_semgrep_bad_override_fails_loudly_naming_override).
  - [ACCEPTED] Minor: override branch uses `.exists()` (file or dir) while the
    cache branch uses `.is_dir()`. Intentional — an override may legitimately be
    a single rules file; the cache is always a directory. Documented in
    code-review.toml.example.
  - [ADDRESSED] Minor: override-precedence coverage — covered by
    test_semgrep_override_takes_precedence_over_cache; missing-override now by
    test_semgrep_bad_override_fails_loudly_naming_override.
  - 2 Nit findings dropped (per SDLC).
---

# s0-t2 — Adapter: cache_root resolution, loud fallback, drop unsupported flag

## Outcome

The semgrep adapter resolves its rules dir through `cache_root()` (honoring
`$POLYREVIEW_CACHE_DIR`), fails loudly instead of running the broken
`--config auto` + `--metrics off` combination, and stops passing the
unsupported `--x-ignore-semgrepignore-files` flag. Implements s0-t0's decisions
#3–#5. Depends on s0-t0.

## Acceptance criteria

### Scenario: rules dir resolves through cache_root()
- **Given** `$POLYREVIEW_CACHE_DIR` set to a dir containing `cache/semgrep/rules`
- **When** the adapter builds its command
- **Then** `--config` points at that dir (not a `Path.cwd()`-derived path).

### Scenario: missing cache fails loudly
- **Given** no `semgrep_rules` override and no provisioned cache
- **When** the adapter runs
- **Then** it returns `status=error` with an actionable message naming
  `scripts/setup.sh` — it does **not** emit `--config auto` together with
  `--metrics off`.

### Scenario: x-ignore-semgrepignore flag handled per ADR scan-scope caveat
- **Given** the built command
- **Then** the `--x-ignore-semgrepignore-files` flag is handled per the ADR's
  scan-scope caveat. **Resolved: kept** — on the pinned semgrep 1.161.0 the flag
  is load-bearing (without it, semgrep's default `.semgrepignore` excludes
  `tests/` and findings there are silently lost; verified empirically). The pin
  is the version guard. (The ADR's earlier "unsupported flag" framing was a
  factual error, corrected in ADR-0016.)

### Scenario: explicit override still works (CLI-wired, if ADR #5 = yes)
- **Given** `code-review.toml` setting a `semgrep_rules` path (or the existing
  `config["semgrep_rules"]`)
- **When** a review runs
- **Then** `--config` uses the override, ahead of the cache dir.

## Test specification

Write first, confirm red, then implement (extend `tests/test_adapters/test_semgrep.py`):

1. `test_semgrep_rules_dir_honors_cache_root`: set `$POLYREVIEW_CACHE_DIR` to a
   `tmp_path` with `cache/semgrep/rules/`; assert the resolved config arg is that
   path.
2. `test_semgrep_missing_cache_returns_error`: no override, empty cache;
   monkeypatch so no real semgrep runs; assert `status=error` and the message
   mentions setup.sh; assert the command (if built at all) never contains both
   `--config auto` and `--metrics off`.
3. `test_semgrep_keeps_x_ignore_flag`: capture the constructed argv; assert
   `--x-ignore-semgrepignore-files` is **present** (load-bearing — see the
   scenario above; the test pins the decision against a future tidy-up).
4. (if ADR #5 = yes) `test_config_parses_semgrep_rules` + a CLI/`load_config`
   test asserting the value reaches `request.config["semgrep_rules"]`.
