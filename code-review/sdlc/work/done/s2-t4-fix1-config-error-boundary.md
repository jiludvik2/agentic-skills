---
id: s2-t4-fix1
kind: fix-task
project: code-review
status: done
parent: s2-t4-cli-wiring-and-schema-validation
created: 2026-05-26
updated: 2026-05-26
---

# s2-t4-fix1: ConfigError escapes main() as raw traceback

## Finding (from reviewer)

Important: `load_config(_SKILL_DIR)` could raise `ConfigError` on malformed TOML; the call was
uncaught in `main()`, producing a raw Python traceback instead of a clean error message + exit 1.

## Fix

Wrapped `load_config()` call in `try/except ConfigError as exc:` block; echoes message to stderr
and raises `typer.Exit(1) from exc`.

Also added two Minor coverage tests:
- `test_missing_schema_file_skipped_silently`: schema path absent → CLI continues normally
- `test_config_error_exits_cleanly`: ConfigError → non-zero exit, clean message, no traceback

## Verification

116 tests pass. ruff + mypy strict clean.
