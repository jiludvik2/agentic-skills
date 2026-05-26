---
id: s0-t2-cli-skeleton
kind: task
project: code-review
status: done
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t2 — CLI skeleton and paths module

## Outcome

`python -m code_review.cli --help` exits 0 and lists all expected flags. `code_review/paths.py` resolves all skill-relative paths from a single anchor. `--output` outside CWD is rejected at argument-parse time with a sandbox explanation before any analysis runs.

## Acceptance Criteria

- `python -m code_review.cli --help` exits 0; stdout mentions `--analyzer`, `--target`, `--diff`, `--output`, `--capabilities`.
- `python -m code_review.cli --capabilities` exits 0 and emits valid JSON (stub object; full implementation in s1).
- Invoking with `--analyzer semgrep --target .` but no adapters wired exits non-zero with a clean error (no unhandled traceback in stderr).
- `--output /tmp/x.json`, `--output ~/x.json`, `--output /etc/anything` each exit non-zero before any analysis runs; the error message contains `"sandbox"` (or `"CWD"`); no file is written outside CWD.
- `--output <path inside CWD>` is accepted (no rejection).
- The CWD guard uses `Path.resolve()` on both the output path and `Path.cwd()` before comparing, so symlinks inside CWD are accepted.
- `code_review/paths.py` exports `SkillPaths` with `skill_root: Path`, `runs_dir: Path`, and `cache_dir: Path` as computed properties; both dirs are subdirectories of `skill_root`.
- `mypy --strict` passes on `cli.py` and `paths.py`.

## Test specification

`tests/test_cli.py` — written first:

- `test_help_exits_zero` — `subprocess.run(["python", "-m", "code_review.cli", "--help"])`; assert returncode == 0; assert `"--analyzer"` and `"--output"` in stdout.
- `test_capabilities_stub_exits_zero` — run `--capabilities`; assert returncode == 0; assert `json.loads(stdout)` succeeds.
- `test_output_tmp_rejected` — `--output /tmp/x.json`; assert returncode != 0; assert `"sandbox"` or `"CWD"` in combined stdout+stderr; assert `/tmp/x.json` does not exist after.
- `test_output_home_rejected` — same with `--output ~/review.json`.
- `test_output_etc_rejected` — same with `--output /etc/review.json`.

`tests/test_paths.py` — written first:

- `test_skill_paths_dirs_inside_root` — `SkillPaths(skill_root=tmp_path)`; assert `paths.runs_dir.is_relative_to(tmp_path)` and `paths.cache_dir.is_relative_to(tmp_path)`.
- `test_cwd_guard_accepts_symlink_inside_cwd` — create a symlink inside `tmp_path` pointing within `tmp_path`; run CLI with `--output <symlink_path>`; assert not rejected by the CWD guard (may fail downstream because no adapter is wired — that is acceptable as long as the error is not "outside CWD").
