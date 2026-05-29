---
id: s3-t1-rename-pypi-and-binary-and-docs
kind: task
project: code-review
status: active
parent: s3-multi-agent-rename
sources: [s3-multi-agent-rename]
status: done
created: 2026-05-29
updated: 2026-05-29
notes: |
  Verify PASS (all ACs evidenced; 337 passed, ruff+mypy clean). Review MINOR-ONLY:
  one Minor (README migration note claimed the package "was previously published",
  but it was never published) — resolved in-task by rewording to "early development
  used the working name … renamed before its first release". Nit (stale
  claude-code-review framing in STATE.md) deferred to Wrap. ADR-0013 also annotated
  with a rename pointer (bonus, beyond task scope, consistent with ADR-0012).
---

# s3-t1 — atomic rename: PyPI dist + binary + docs + release.yml

## Outcome

Rename the distribution and console binary `claude-code-review` → `polyreview` across packaging, version lookup, the release workflow, and all user-facing docs — in a single commit, so the working tree never sits in a half-renamed state. Python import name `code_review` is untouched.

## Acceptance criteria

Satisfies story scenarios: **"PyPI distribution renamed"**, **"Console binary renamed, source-checkout fallback preserved"**, **"Documentation reflects the new name"**, **"Migration note explains the rename"**.

**Packaging / code:**
- `pyproject.toml`: `[project].name == "polyreview"`; `[project.scripts] == {"polyreview": "code_review.cli:app"}` (binary renamed, entry-point target unchanged).
- `code_review/__init__.py`: `importlib.metadata.version("polyreview")`.

**Release workflow (gap folded in from the story-level note):**
- `.github/workflows/release.yml`: `name:` → "Release polyreview"; the `test-dist` smoke step invokes `polyreview --capabilities` (was `claude-code-review --capabilities`).
- **Unchanged:** the `on.push.tags` trigger `code-review-v*` and the `publish` job's tag-validation regex `^code-review-v…$` — per ADR-0014 the tag prefix is deliberately retained.

**Docs (every install/invocation example uses `polyreview …`):**
- `README.md`: title `# polyreview`; all 8 sites; new one-paragraph migration note in the Status section naming the previous `claude-code-review` distribution, stating it is superseded by `polyreview`, and the multi-agent rationale. SKILL.md Developer-note `python -m code_review.cli` source-checkout fallback preserved.
- `.claude/skills/code-review/SKILL.md`: the 7 invocation examples + the wheel-layout parenthetical; keep the `python -m code_review.cli` fallback wording.
- `sdlc/docs/runbooks/release.md`: title, examples, and the **Trusted Publisher binding Project Name → `polyreview`** in both the PyPI and TestPyPI sections and the first-release checklist; add a "Rename history" subsection carrying the migration note.
- `sdlc/docs/decisions/adr-0012-pypi-publication.md`: annotate with a cross-reference to ADR-0014 for the distribution name — do not rewrite the historical decision.

## Test specification

Per the story "Test specification", updated in the same commit as the rename:

- `tests/test_pyproject_metadata.py` — `test_name_is_claude_code_review` → assert name `"polyreview"`; `test_console_script_is_claude_code_review` → assert `{"polyreview": "code_review.cli:app"}`. Rename both test functions to match.
- `tests/test_version_source.py` — metadata lookup target `"claude-code-review"` → `"polyreview"` (3 sites); add `test_version_lookup_uses_new_distribution_name` asserting `code_review/__init__.py` calls `version("polyreview")`.
- `tests/test_console_script_install.py` — install the built wheel, invoke `<venv>/bin/polyreview --capabilities`, assert JSON validity; update docstring + binary path.
- `tests/test_skill_md_invocation.py` — leader assertion `startswith("polyreview")`.
- `tests/test_scaffold.py` — name + scripts assertions → `polyreview`.
- **Release-workflow guard:** extend the existing release-workflow structural test if one exists; otherwise add `tests/test_release_workflow_binary.py` asserting the `test-dist` step references `polyreview --capabilities` and contains no `claude-code-review`, and that the `code-review-v*` tag trigger is still present (guards the deliberate asymmetry).
- Regression: full suite green; `uv run ruff check .` + `uv run mypy` clean. (Pre-existing mypy `conftest.py: Source file found twice` carried unchanged.)

## Notes

- Atomic: one commit, message `code-review s3-t1: rename claude-code-review → polyreview (dist + binary + docs + release.yml)`.
- README + runbook content: Claude drafts, operator approves before commit.
- Run all tooling via `uv run` (project venv is uv-managed 3.12).
