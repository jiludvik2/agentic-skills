# State — last updated 2026-05-29

**Active focus:** none — `epic-deployment-readiness` **closed** (s0–s3 done, s0-t6 folded in). Between epics; awaiting operator direction on the next one.
**Last completed:** Epic close (`9da2a1f`). First release validated end-to-end: **`polyreview 0.1.0rc1` published to TestPyPI** via `release.yml` (run 26645884515, all jobs green; PyPI step skipped for the `-rc` tag). s0-t6 cache-path unification (ADR-0015) landed in the same batch.
**Next:** operator decision on the next epic, plus the two follow-ups below.

## Open questions / follow-ups

- **GA release to PyPI.** Only TestPyPI has `0.1.0rc1` so far. To ship for real: bump `pyproject.toml` to `0.1.0` (drop `rc1`), commit, then cut + push the GA tag `code-review-v0.1.0` (no `-rc` → routes to the `pypi` environment). Per SDLC, the GA release tag is operator-created. Runbook: `sdlc/docs/runbooks/release.md`.
- **`claude-code-review` redirect meta-package.** Deferred follow-up (ADR-0014): publish a thin `claude-code-review` depending only on `polyreview`, once `polyreview` has its first GA publish.
- **CI failing on `main`.** Pre-existing; the push of `main` will have triggered another CI run — expect it red for the same pre-existing reason (independent of `release.yml`, which is green). Worth a dedicated debugging session.
- **Pre-existing mypy `conftest.py: Source file found twice`** when mypy points at `tests/` — carried unchanged.

## Recent shipped (2026-05-29)

- **s3-multi-agent-rename** (`7dba060`→`0c63b94`): `claude-code-review` → `polyreview` across packaging/binary/release.yml/docs/tests; AGENTS.md canonical + CLAUDE.md redirect; ADR-0014. Kept: import name `code_review`, skill bundle path, `code-review-v*` tag prefix.
- **s0-t6** (`4615b0b`): single cache-path resolver `code_review.paths.cache_root()` (`$POLYREVIEW_CACHE_DIR` else CWD-anchored); ADR-0015.
- **First release** (`code-review-v0.1.0-rc1` → TestPyPI). All work pushed to origin/main (`@{u}..HEAD` empty).
