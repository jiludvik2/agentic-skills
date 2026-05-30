# Raw capture — vendor JS semgrep rules into the ruleset (closes G6)

**Captured:** 2026-05-30
**Origin:** coverage dogfood (NodeGoat JS, 184 findings, 0 first-party SAST). Closes the
**G6** gap from `sdlc/raw/post-coverage-eval-findings.md`; extends **G4/F5** (semgrep thinness).

## The thought

Add JavaScript/TypeScript rules to polyreview's **vendored semgrep ruleset** so semgrep emits
real first-party JS SAST findings. This is the cheapest path to closing G6 — no new analyzer,
config change only.

## Why this is the right lever (verified 2026-05-30)

- The semgrep **engine already supports JS/TS** (~30 languages). The 0-findings result on
  NodeGoat is a *ruleset* limitation, not a tool limitation.
- The vendored ruleset (`cache/semgrep/rules/security.yaml`, shipped via `scripts/setup.sh` /
  the `_bundle/`) currently holds **exactly two rules, both `languages: [python]`**:
  `subprocess-shell-true`, `dangerous-eval`.
- The adapter (`code_review/adapters/semgrep.py:78`) pins `--config` to that local dir and
  **deliberately has no `--config auto`/registry fallback** (incompatible with `--metrics off`,
  adapter lines 47–52). So semgrep never reaches the registry where JS rulesets live.
- Contrast bandit: architecturally Python-only (AST scanner). G6 is **not** closable via bandit —
  semgrep is the only in-suite tool that *can* do JS SAST.

## Scope sketch (not decided — for compile to shape)

- Vendor a JS/TS security ruleset into the local `security.yaml` (candidates: hand-picked subset of
  `p/javascript`, `p/nodejs-scan`-style rules — injection (SQL/NoSQL/command), XSS, SSRF, eval,
  insecure deserialization, hardcoded secrets, weak crypto). Keep it vendored/pinned (offline,
  `--metrics off`-compatible) — do **not** switch to `--config auto`/registry.
- Re-run the NodeGoat dogfood as the acceptance oracle: expect non-zero first-party JS findings
  landing on the documented `app/views/tutorial/a*.html` lab targets.
- Revisit ADR-0016 (vendored-ruleset rationale) — the "Python-first" framing becomes
  "Python + JS first-party SAST". Update capabilities/`lang_select` if semgrep is currently
  treated as Python-only there.
- Watch interaction with **G1** (jscpd scope leak) and JS lang-detection — adding JS semgrep
  coverage shouldn't be conflated with the jscpd `--format` fix.

## Open questions for compile

- Story or epic? Likely a single story under the next analyzer round (sibling to G6/G7/G1).
- Rule-curation policy: how many rules, maintenance burden of a hand-vendored JS set vs. tracking
  an upstream pack at a pinned commit.
- Test fixtures: add JS SAST fixtures to the analyzer-coverage QA harness so JS coverage is
  guarded by CI, not just the NodeGoat manual dogfood.
