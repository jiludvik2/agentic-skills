---
id: s1-t1c-migrate-schemathesis
kind: task
project: code-review
status: done
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0021-remove-schemathesis-from-scope.md, adr-0020-thin-invocation-runner.md, s1-migrate-adapters-and-emit-bundle.md]
created: 2026-05-30
updated: 2026-05-31
tags: [removal, schemathesis, contract-testing, scope, capabilities]
---

# Task s1-t1c — remove Schemathesis + the contracts domain from code-review

> **Scope change (operator-directed, 2026-05-31).** This task was originally "migrate
> schemathesis to a subprocess." Execution hit the auth/redaction autonomy-gate fork
> (`schemathesis run` only takes auth on `argv`; the thin runner serialises
> `CaptureOutput.command` into the bundle → token leak). The operator decided to **remove
> Schemathesis from code-review entirely** and spin contract testing out as a separate
> skill. See **ADR-0021**. The id is kept stable per SDLC rule #5.

## Outcome

Schemathesis and the entire `contracts` review domain are removed from code-review: no
adapter, no registry entry, no `contracts` domain / `contract-verification` category in the
selectable taxonomy, no `contract_testing` config, no Schemathesis-only dependencies. The
full suite is green with those surfaces gone; `--review contracts` is an unknown-domain
error. Contract testing is captured as a future standalone skill (not built here).

## Acceptance criteria

- `grep -ri schemathesis code_review/` is clean (no adapter, import, registry entry,
  capabilities entry, or doc reference in the live package).
- `capabilities.json` has no `schemathesis` analyzer, no `contracts` domain, no
  `contract-verification` category; the review-selection resolver rejects `--review contracts`.
- `config.py` / `cli.py` carry no `contract_testing` field or plumbing.
- `pyproject.toml` and `stack-pins.md` no longer pin `schemathesis`, `hypothesis`,
  `fastapi`, or `uvicorn`.
- `tests/test_adapters/test_schemathesis.py` and `tests/fixtures/schemathesis-target/` are
  deleted; multi-adapter tests (review-selection, capabilities, config, CLI-error,
  pyproject-metadata, toml-template, sandbox-compat) no longer reference schemathesis/contracts.
- The generic `scope_restrictions` mechanism stays covered (test uses a generic
  story-level-only stub, not a Schemathesis-named one).
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.
- ADR-0021 filed; ADR-0009 marked superseded; SKILL.md / README / architecture doc no longer
  advertise contract testing; future-skill idea captured to `/sdlc/raw/`.

## Test specification (removal — confirm RED→GREEN by deletion/adjustment)

Removal is driven by making the suite coherent without schemathesis:
1. Delete `test_schemathesis.py` + the `schemathesis-target` fixture.
2. Update `test_review_selection_{resolution,validation,combinations}.py` to drop the
   `contracts`-domain / schemathesis cases and **add/keep a test asserting `--review
   contracts` now errors as an unknown domain** (the positive assertion of removal).
3. Update `test_capabilities.py`, `test_config.py`, `test_cli_error_branches.py`,
   `test_pyproject_metadata.py`, `test_toml_example_template.py`,
   `test_sandbox_compatibility.py` to drop schemathesis/contract references.
4. Rename the `test_scope_restrictions.py` stub to a generic story-level-only adapter so the
   mechanism stays tested without naming a deleted analyzer.

## Notes

- Decisions confirmed by operator (2026-05-31): remove the `contracts` domain entirely
  (not a stub); remove all four deps (schemathesis/hypothesis/fastapi/uvicorn).
- Historical analyzer-coverage QA snapshots mentioning Schemathesis are dated records — left as-is.

## Close (DONE 2026-05-31)

Verify **PASS** (all 8 ACs; ~1782 deletions across 28 files; full suite **431 passed**, ruff +
`mypy code_review` clean; `uv.lock` synced, −783 lines).

Review **HAS-CRITICAL-OR-IMPORTANT → remediated inline before close** (no fix task filed; the
finding was a doc-coherence gap squarely inside this task's remit and fixed directly):
- **Important** — ADR-0021 declared it amends ADR-0011, but ADR-0011 still advertised the removed
  `contracts`/`conformance`/`schemathesis` taxonomy with no banner. **Fixed:** added the
  "Amended by ADR-0021" banner + historical-scope note to ADR-0011 (matching the ADR-0009 convention).
- **Minor** — future-skill seed didn't record the `schemathesis → pytest>=8,<9` transitive
  constraint. **Fixed** in `sdlc/raw/contract-testing-skill.md`.
- **Minor** — SKILL.md "Warnings and errors" no longer illustrated retired-domain behaviour.
  **Fixed:** one line noting `contracts`/`conformance` now surface as unknown-value errors.
- **Nit** — removal-assertion tests asserted only the echoed token. **Fixed:** also assert the
  "Unknown" rejection prefix.

Carried (not blocking): `capabilities.json` retains a `fastapi` entry under
`stack_coverage.python.frameworks` — a *target framework code-review reviews* ("planned"), unrelated
to the removed fixture dep; left intentionally. Architecture doc keeps Schemathesis prose under a
supersede banner (matching its Pact convention) rather than excising 26 inline mentions.
