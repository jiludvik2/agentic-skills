---
id: s2-t1-remove-dead-sarif-schema
kind: task
project: code-review
status: active
parent: s2-skill-interpretation-and-golden-bundle
sources: [adr-0020-thin-invocation-runner.md, s1-t3-cli-bundle-and-delete-sarif-layer.md, intent-review-requirements.md]
created: 2026-05-31
updated: 2026-05-31
tags: [cleanup, schema, packaging, sarif]
---

# Task s2-t1 — remove the dead `sarif-2.1.0.json` schema

## Outcome

`code_review/schemas/sarif-2.1.0.json` and its packaging-test pins are gone. The wheel no
longer ships dead package data, and no test asserts a schema that nothing loads.

## Context — operator decision 2026-05-31: **remove**

After `sarif_utils.py` was deleted in s1-t3, nothing in `code_review/` loads or validates
against this schema (`grep -r sarif` in `code_review/*.py` is empty; eslint/trivy still emit
SARIF to stdout but it is captured **raw** — never validated). ADR-0020: code-review emits raw
bundles, not SARIF. The schema's only forward use is as a reference for the future
`intent-review` sibling project (intent-review-requirements.md A2), which will **vendor its own
copy** when bootstrapped — code-review need not carry it.

## Design

- Delete `code_review/schemas/sarif-2.1.0.json`.
- Drop the schema from the 3 packaging pins:
  - `tests/test_package_data_resources.py:16` — remove `"schemas/sarif-2.1.0.json"`.
  - `tests/test_wheel_packaging.py:27` — remove `"code_review/schemas/sarif-2.1.0.json"`.
  - `tests/test_scaffold.py:25` — remove the `sarif-2.1.0.json` existence assertion.
- Check `pyproject.toml` / `MANIFEST.in` for an explicit `schemas/*.json` glob vs an explicit
  file list; if the schema is listed by name, drop it. (A glob needs no change.)
- Update `intent-review-requirements.md` §References: note the SARIF finding-format schema is
  no longer carried in `code-review`; intent-review vendors its own when that project is
  initialised (cite ADR-0020's amendment to ADR-0010).

## Acceptance criteria

- `code_review/schemas/sarif-2.1.0.json` does not exist.
- `grep -r "sarif-2.1.0"` over `code_review/` and `tests/` returns nothing (outside this task's
  own deletion diff).
- The remaining `schemas/` data (`review-bundle.v1.json`, `review-request.json`,
  `capabilities.json`) still resolves via `importlib.resources` and the packaging tests pass.
- The wheel-packaging and package-data tests pass with the schema removed (they no longer pin
  it).
- `intent-review-requirements.md` records where the SARIF schema went.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.

## Test specification (write first, confirm RED)

1. Update the 3 pinning tests to drop the schema entry — RED first (the unedited tests still
   demand the file, which we are deleting), then GREEN after the edits + deletion.
2. Add `tests/test_package_data_resources.py::test_no_dead_sarif_schema` (or similar): assert
   `importlib.resources.files("code_review") / "schemas" / "sarif-2.1.0.json"` does **not**
   exist — a guard against it being re-added without a loader.
3. Existing `test_package_data_resources` / `test_wheel_packaging` must still pass for the
   live schemas (regression: the other three JSON contracts are unaffected).

## Notes

- Pure deletion + test edits. No runtime code path touches this schema, so there is no
  behavioural risk — the only risk is a stray packaging reference, which the grep AC catches.
