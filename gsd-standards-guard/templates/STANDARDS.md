# Coding standards

> **Authoring note (gsd-standards-guard).** Code-level conventions — the *how we
> write it* rules that apply across the codebase. Sits below the ADRs in the
> authority order: `docs/adr/*` (binding decisions) > **this file** >
> `docs/ARCHITECTURE.md`. Where a convention is decision-shaped and load-bearing
> (a real tradeoff future work must not reverse), promote it to an ADR and add a
> row to the standing-rule ledger + `docs/adr/index.yaml` instead of burying it
> here. Keep this file to conventions that are broadly true and rarely contested.

## Naming

- {Casing per language (e.g. snake_case functions/vars, PascalCase types).}
- {Domain vocabulary — the canonical name for each core concept; avoid synonyms.}

## Module shape

- {How a module/package is organized; what a public surface looks like vs internals.}
- {Where cross-cutting concerns (config, logging, errors) are allowed to live.}

## Data contracts

- {How data crossing a boundary is typed/validated; where schemas live.}
- {Null / optional semantics; how absent vs empty is represented.}

## Error handling

- {Exceptions vs result types; what may swallow an error and what must propagate.}
- {The error shape returned across the API/serving boundary.}

## SQL / persistence safety

- {Parameterization rule — no string-interpolated SQL.}
- {Where DDL may run; migration discipline. (Often ADR-governed — cross-reference.)}

## Logging & observability

- {Levels, structured vs freeform, what must never be logged (secrets, PII).}

## Complexity & size

- {Function/file size or cyclomatic-complexity ceilings, if any.}
- {When to split vs inline.}

## Testing

- {What must have tests; unit vs integration boundary; fixture conventions.}

---

*A convention here is advisory unless an ADR makes it binding. When a reviewer
finds code contradicting this file, it is a finding; cite the section.*
