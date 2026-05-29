---
id: s2-t5-skill-md-and-setup-script-fixes
kind: task
project: code-review
status: done
parent: s2-packaging-hardening
created: 2026-05-29
updated: 2026-05-29
closed: 2026-05-29
verify: PASS (commit 039b2ed; 326 passed + 6 skipped + 8 deselected; ruff clean; mypy clean; 5 new tests)
review: MINOR-ONLY (2 Minor + 1 Nit). Both Minors resolved in close commit: (a) setup.sh BUNDLE_DIR-empty degenerate branch now prints a clear "skill bundle not located" diagnostic and skips step 5's body, instead of emitting a phantom leading-slash path; (b) test_no_primary_module_invocations now scans every non-comment line in each fenced block (not just the leader), catching the `# comment` followed by `python -m code_review.cli` pattern that would otherwise slip through. Nit (developer-note paragraph could be split) dropped — single dense paragraph reads fine; splitting would be churn.
---

# s2-t5 — SKILL.md binary invocation + `setup.sh` example-path fix

## Outcome

Two small but visible defects, grouped because they both live at the skill-bundle boundary:

1. **`SKILL.md` invocation lines lead with the installed binary**, not the `python -m code_review.cli` module form. The module form silently breaks when the package is installed via `pipx install claude-code-review` or `uv tool install claude-code-review` (isolated venv, not on `sys.path` for arbitrary `python` invocations). After s1's PyPI publication work, the binary `claude-code-review` is the canonical entry point.

2. **`scripts/setup.sh` step 5 ("Starter config template") locates the bundled example correctly.** Currently `EXAMPLE_PATH="${SKILL_ROOT}/code-review.toml.example"` resolves to `code-review/code-review.toml.example` — which doesn't exist; the example file actually lives at `.claude/skills/code-review/code-review.toml.example`. Step 5 always prints `missing: …` in the developer layout. Fix by introducing a `BUNDLE_DIR` variable that resolves to the skill-bundle subdirectory.

## Acceptance criteria

### SKILL.md

- Every code block currently using `python -m code_review.cli [...]` as the primary invocation leads with `claude-code-review [...]` instead. There are 7 sites (per `grep -n "python -m code_review"` on the current file).
- A single short paragraph after the Invocation block acknowledges the module form (`python -m code_review.cli`) works in a source checkout — the developer/SDLC context where `SKILL.md` is also read. The module form is NOT presented as a primary alternative in any subsequent example.
- No regression: the existing test `tests/test_skill_scaffold.py` continues to pass; SKILL.md still parses (no broken markdown links, no orphan code fences).

### `scripts/setup.sh`

- A new `BUNDLE_DIR` (or equivalent name) is computed at script start, resolving to `<repo>/.claude/skills/code-review/` in the developer layout, or to the bundle dir when installed under `<host>/.claude/skills/code-review/`.
- `EXAMPLE_PATH` is rebound to `${BUNDLE_DIR}/code-review.toml.example`.
- Running `./scripts/setup.sh` in dev layout prints `available: <abs path to existing file>` for step 5 (not `missing`), and exits 0.
- Existing `SKILL_ROOT`-based logic in earlier steps (Python deps, JS deps, prefetch) is unchanged.

## Test specification

- **New: `tests/test_skill_md_invocation.py`** with three assertions:
  1. `test_invocation_block_leads_with_binary` — find the Invocation section's first fenced code block; assert its first non-blank line starts with `claude-code-review`.
  2. `test_no_primary_module_invocations_in_examples` — every fenced code block in the file is scanned; if it contains `python -m code_review.cli` on the first non-blank line, the test fails. A later line mentioning the module form (in a prose paragraph or a "Developer note" block) is allowed.
  3. `test_developer_note_present` — assert the file contains a paragraph (outside any code block) acknowledging the module-form fallback for source checkouts; concrete check is `python -m code_review.cli` appearing in prose with a "source checkout" or "developer" or "dev mode" nearby context.
- **New: `tests/test_setup_sh_bundle_dir.py`** with two assertions:
  1. `test_setup_sh_defines_bundle_dir` — read `scripts/setup.sh` source; assert a `BUNDLE_DIR=` assignment exists and references `.claude/skills/code-review` somewhere on its right-hand side (or in an immediately-following dirname/cd chain).
  2. `test_example_path_resolves_in_dev_layout` — programmatically extract the resolved value (run setup.sh through a `bash -c` that sources function definitions only, or use `bash -c "source script ; echo $EXAMPLE_PATH"`); assert the resulting path equals the actual file at `<repo>/.claude/skills/code-review/code-review.toml.example` and that the file exists.
- **Regression**: existing tests continue to pass; `ruff` + `mypy` clean.

## Notes

- The system sandbox blocks writes under `.claude/skills/code-review/` via Bash tools but NOT via the Edit/Write tools — SKILL.md edits go via Edit; new test files go in `tests/` (no sandbox issue).
- Don't touch the SKILL.md frontmatter (`name`, `description`) — Claude Code uses those for auto-selection.
- The "Developer note" paragraph for the module-form fallback should be tucked into the existing "Invocation" section right after the AC-relevant primary block, not added as a new top-level section. The page is already long.
- For test #2 on `setup.sh`: sourcing the whole script would execute all the steps. Use a subshell with `set -n` (parser-only) plus `bash -n` won't expose variables. The cleanest approach is to use `bash -c 'source <(sed -n "1,/^step \"Python/p" scripts/setup.sh) ; echo $BUNDLE_DIR; echo $EXAMPLE_PATH'` — extract just the variable-definition prelude. Or simpler: regex-match the assignment in the source text and resolve manually. I'll choose the simpler regex-match approach at execution time.
