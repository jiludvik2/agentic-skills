---
id: s1-t0-skill-scaffold-and-schemas
kind: task
project: code-review
status: done
parent: s1-reviewer-skill-and-capabilities
created: 2026-05-26
updated: 2026-05-26
---

# s1-t0 — Skill scaffold, SKILL.md, and contract schemas

## Outcome

The skill is discoverable at `.claude/skills/code-review/SKILL.md` with the required documentation sections, and three JSON Schemas (`schemas/capabilities.json`, `schemas/review-request.json`, `schemas/review-response.json`) exist and are valid draft 2020-12 schemas.

## Acceptance Criteria

- `.claude/skills/code-review/SKILL.md` exists with YAML frontmatter containing `name` and `description` fields (Claude Code skill convention).
- SKILL.md body contains, by header presence: "Review scopes" (naming all three values `lite`, `standard`, `full`), "Install" (referencing `./scripts/setup.sh`), "Configure" (showing `review_scope = "standard"` with all three values), and "Sandbox configuration" (containing a fenced JSON code block that parses as valid `settings.json`).
- SKILL.md references `capabilities.json`, `schemas/review-request.json`, and `schemas/review-response.json` by path.
- `schemas/capabilities.json` is a valid JSON Schema (draft 2020-12) describing the `capabilities.json` shape (`review_kinds`, `stack_coverage`, `analyzers`, `taxonomies`).
- `schemas/review-request.json` and `schemas/review-response.json` are valid JSON Schemas describing the s0 CLI input args and consolidated output shape respectively.

## Test specification

New `tests/test_skill_scaffold.py`:

- `test_skill_md_exists_with_frontmatter` — assert file exists; parse frontmatter; assert `name` and `description` keys present and non-empty.
- `test_skill_md_has_required_sections` — assert headers "Review scopes", "Install", "Configure", "Sandbox configuration" present; assert "Review scopes" section text contains `lite`, `standard`, `full`.
- `test_skill_md_sandbox_snippet_is_valid_json` — extract the fenced JSON block under "Sandbox configuration"; assert `json.loads` succeeds.
- `test_skill_md_references_schemas` — assert SKILL.md text references `capabilities.json`, `schemas/review-request.json`, `schemas/review-response.json`.
- `test_contract_schemas_are_valid_jsonschema` — for each of the three schemas, load and call `jsonschema.Draft202012Validator.check_schema(schema)`; assert no exception.
- `test_review_response_schema_matches_s0_output` — build a sample consolidated output dict (the shape `cli._run_analyzers` returns) and validate it against `schemas/review-response.json`.

## Notes / deferrals

- Real `setup.sh` and cache prefetch → s1-t3. Sandbox-installable integration property (no prompts inside `/sandbox`) → exercised manually / deferred as an `@pytest.mark.integration` placeholder, not a unit test this task.
