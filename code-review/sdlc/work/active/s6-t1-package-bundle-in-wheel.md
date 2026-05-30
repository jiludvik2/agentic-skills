---
id: s6-t1-package-bundle-in-wheel
kind: task
project: code-review
status: active
parent: s6-install-into-claude
sources: [pyproject.toml, tests/test_wheel_packaging.py, .claude/skills/code-review/SKILL.md]
created: 2026-05-30
updated: 2026-05-30
tags: [packaging, wheel, hatch, install]
---

# s6-t1 — Package the skill bundle into the wheel

## Outcome

A `pip install polyreview` carries the skill-bundle assets (the s6-t0 manifest:
`SKILL.md`, `code-review.toml.example`, `semgrep-rules/security.yaml`,
`package.json`, `package-lock.json`) so the s6-t2 `install` command has something
to copy. Today the wheel ships only `code_review/` + `capabilities.json` +
`schemas/*.json` (`pyproject.toml` `[tool.hatch.build.targets.wheel].include`);
the bundle assets at `.claude/skills/code-review/` are outside the package and
absent from the wheel. Depends on the manifest decided in s6-t0.

## Acceptance criteria

### Scenario: built wheel contains every manifest asset
- **Given** a wheel built from this repo (`uv build` / `hatch build`)
- **When** its contents are listed
- **Then** every asset in the s6-t0 bundle manifest is present and readable via the
  mechanism the install command will use (`importlib.resources` over the package,
  or a documented package-data path).

### Scenario: provisioned/produced dirs are not shipped
- **Given** the built wheel
- **When** its contents are listed
- **Then** `node_modules/`, `cache/`, and `runs/` are **not** in the wheel (they are
  host-provisioned/produced, not shipped).

### Scenario: no duplication / single source of truth
- **Given** the bundle assets exist once in the repo
- **When** the wheel is built
- **Then** packaging references the existing files (force-include / package-data),
  not a second committed copy that could drift from `.claude/skills/code-review/`.

## Test specification

Write first, confirm red, then implement. Extend `tests/test_wheel_packaging.py`
(it already builds a wheel in a tmp dir and asserts bundled JSON is intact — reuse
that harness; it is marked `slow`):

1. `test_wheel_contains_skill_bundle`: build the wheel, assert each manifest asset
   (`SKILL.md`, `code-review.toml.example`, `semgrep-rules/security.yaml`,
   `package.json`, `package-lock.json`) is present in the wheel.
2. `test_wheel_excludes_provisioned_dirs`: assert no `node_modules/`, `cache/`, or
   `runs/` entries are in the wheel.
3. If the chosen mechanism exposes the assets through `importlib.resources`
   (recommended, mirroring `_CAPABILITIES_PATH`/`_SCHEMA_PATH` in `cli.py`), a unit
   test that `importlib.resources.files("code_review")` can locate `SKILL.md` from
   the installed layout.

## Notes

Decide force-include vs. relocating the bundle assets under `code_review/` in
s6-t0's manifest decision. Prefer force-include so the repo's
`.claude/skills/code-review/` stays the canonical on-disk bundle (the dev sibling
layout) and the wheel just mirrors it — avoids moving files that the QA smoke
harness and `setup.sh` already reference by their current paths.
