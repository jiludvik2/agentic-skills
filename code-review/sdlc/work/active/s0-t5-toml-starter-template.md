---
id: s0-t5-toml-starter-template
kind: task
project: code-review
status: done
parent: s0-deployment-layout-fixup
created: 2026-05-28
updated: 2026-05-28
---

# s0-t5 — Bundled `code-review.toml.example` starter template

## Outcome

Ship a well-commented `code-review.toml.example` in the skill bundle. `setup.sh` prints its absolute path plus a one-line copy hint at the end of installation. The example documents every key the `Config` dataclass accepts.

## Acceptance criteria

- A new file at `.claude/skills/code-review/code-review.toml.example` exists in the repo, containing:
  - A header comment block (3–5 lines): purpose, copy-instructions hint, link to SKILL.md.
  - Every key from `code_review/config.py`'s `Config` dataclass, shown commented-out with: one-line purpose, default value, example value. Specifically:
    - `dedup_line_tolerance` (int, default 3)
    - `severity_overrides` (table; example `"semgrep:python.lang.security.audit.weak-crypto" = "important"`)
    - `hotspot_weights` (table; example weights for `severity_weighted_findings`, `cyclomatic_complexity`, `coupling`)
    - `disabled_analyzers` (list; example `["trivy"]`)
    - `contract_testing` (table; example with `schemathesis_target` and `auth.token_env`)
- The file parses with `tomllib.loads(...)` after uncommenting (or as-is, depending on TOML syntax for commented-out blocks).
- `setup.sh` step 5 (new): "Starter config template" — prints the absolute path of `code-review.toml.example` and a hint: `Copy to <host_root>/code-review.toml (or wherever you'll invoke the CLI from) to override defaults.` The host root is resolved via the existing `find_host_root`; if no `.claude/` ancestor resolves, prints a generic hint without a concrete path.
- `.claude/skills/code-review/SKILL.md` documents the example file under the Install section: "After install, copy `code-review.toml.example` to your project root and edit. See the file's own comments for each tunable key."

## Test specification

- **New: `tests/test_toml_example_template.py`** — single test that:
  - Asserts `code-review.toml.example` exists at the expected location.
  - Loads the file with `tomllib.loads`; the *uncommented* form parses cleanly.
  - Copies the example into `tmp_path / "code-review.toml"`, uncomments all key lines (script the un-commenting; it's the example-as-shipped state minus the leading `# ` from key lines), invokes `load_config(tmp_path / "code-review.toml")`, and asserts the resulting `Config` has all keys reflecting the example's documented values.
- **Updated: `tests/test_config_lookup.py`** (from `s0-t2`) — add a case: with the example file copied as `./code-review.toml`, the CLI honours the example's `dedup_line_tolerance` override.
- **Updated: `tests/test_production_layout.py`** (from `s0-t3`) — extend the smoke test to also copy the example file into the staged tmp dir and verify the overrides take effect (or keep this in scope for `s0-t3` and just reference it here).

## Notes

- The example file lives in the skill bundle (`.claude/skills/code-review/`), not in the Python package — it's not bundled inside the wheel because it's an *operator config*, not *package data*. Documented in `setup.sh` and `SKILL.md`; consumers find it at the install location.
- For wheel installs (`pip install code-review`), the example file isn't shipped (it's outside the package). The release runbook (s1-t5) and README (s1-t1) document where to find a copy: in the repo, in `.github/` artifacts, or paste from the SKILL.md.
- The "uncomment and parse" test pattern depends on how the example is formatted. Prefer TOML's native commenting where every example key is a real TOML line prefixed with `# ` so that find-replace can produce a valid file. Avoid block-comment workarounds.
- Idempotency: `setup.sh` prints the hint every run; it never writes the file itself (per Phase 3's "no writes outside the skill dir" posture, reaffirmed in the install-procedure revisit).
