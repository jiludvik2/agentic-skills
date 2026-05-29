# State — last updated 2026-05-29

**Active focus:** none — `epic-deployment-readiness` **closed** (s0–s3 done, s0-t6 folded in). Between epics; awaiting operator direction on the next one.
**Last completed:** CI hotfix — **`main` CI is green again** (run 26650975118, `dd6e05e`). Fixed the `test_help_exits_zero` failure (real cause: color-enabled CI splits Typer option dashes into separate ANSI spans, so `--analyzer` is non-contiguous; strip ANSI before asserting) and strict-typed the whole test suite (now type-checked in CI alongside `code_review`).
**Next:** operator decision on the next epic, plus the two follow-ups below.

## Open questions / follow-ups

- **GA release to PyPI.** Only TestPyPI has `0.1.0rc1` so far. To ship for real: bump `pyproject.toml` to `0.1.0` (drop `rc1`), commit, then cut + push the GA tag `code-review-v0.1.0` (no `-rc` → routes to the `pypi` environment). Per SDLC, the GA release tag is operator-created. Runbook: `sdlc/docs/runbooks/release.md`.
- **`claude-code-review` redirect meta-package.** Deferred follow-up (ADR-0014): publish a thin `claude-code-review` depending only on `polyreview`, once `polyreview` has its first GA publish.
  _(Resolved 2026-05-29: the long-standing "CI failing on `main`" and the mypy `conftest.py: Source file found twice` items are both fixed — see Recent shipped.)_

## Recent shipped (2026-05-29)

- **CI hotfix** (`1241624`→`dd6e05e`): green `main` again. `test_help_exits_zero` failed only in color-enabled CI — Rich renders each option's two leading dashes as separate ANSI spans, so `--analyzer` is not a literal substring (passes locally piped, fails in CI; width was a red herring). Fix strips ANSI before the assert (repro via `FORCE_COLOR=1`). Also: added `tests/__init__.py` (fixes mypy "Source file found twice"), excluded `tests/fixtures` from mypy, added `types-PyYAML`, strict-typed all 29 test files; mypy now covers `code_review` **and** `tests`. NB: the ANSI fix also rides on branch `ccglass-traffic-analysis` as `2e94aa7` (cherry-pick dup — prefer `main`'s on merge).
- **s3-multi-agent-rename** (`7dba060`→`0c63b94`): `claude-code-review` → `polyreview` across packaging/binary/release.yml/docs/tests; AGENTS.md canonical + CLAUDE.md redirect; ADR-0014. Kept: import name `code_review`, skill bundle path, `code-review-v*` tag prefix.
- **s0-t6** (`4615b0b`): single cache-path resolver `code_review.paths.cache_root()` (`$POLYREVIEW_CACHE_DIR` else CWD-anchored); ADR-0015.
- **First release** (`code-review-v0.1.0-rc1` → TestPyPI). All work pushed to origin/main (`@{u}..HEAD` empty).
