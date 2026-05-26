---
id: s2-t3-config-loader
kind: task
project: code-review
status: active
parent: s2-aggregator-and-severity-mapping
created: 2026-05-26
updated: 2026-05-26
---

# s2-t3 — config loader: code-review.toml aggregation overrides

## Outcome

`code_review/config.py` loads `code-review.toml` from `.claude/skills/code-review/` (if present) and merges operator overrides into the aggregator's defaults: `dedup.line_tolerance` and individual severity-mapping overrides. The aggregator and hotspot functions accept an optional `Config` object; when absent, pure defaults apply.

## Acceptance criteria

- `load_config(skill_dir: Path) -> Config` reads `code-review.toml` if present; returns a `Config` dataclass with defaults for all fields if the file is absent.
- `Config.dedup_line_tolerance: int` defaults to `3`; overridden by `[dedup] line_tolerance = N` in the TOML.
- `Config.severity_overrides: dict[str, str]` defaults to `{}`; overridden by `[severity] <level_combo> = "sdlc_label"` entries.
- `Config.hotspot_weights: dict[str, float]` defaults to the values in `capabilities.json`; entries in `[hotspots.weights]` in the TOML override individual keys.
- `aggregate(outputs, config=None)` and `compute_hotspots(..., config=None)` accept the optional `Config`; when `config` is not `None`, `config.dedup_line_tolerance` replaces the default `3`.
- Severity overrides in `Config` are applied after the base `map_severity` call: if an override maps `"warning+high" → "critical"`, that wins over the default table.
- A malformed TOML (syntax error) raises a clear `ConfigError` with a message citing the file path; it does not silently fall back to defaults.
- The config file path is documented in `SKILL.md` under a `## Configuration` heading (add it in this task if not present).

## Test specification

`tests/test_config.py`:

- **Absent file test** — `load_config` with a dir that has no `code-review.toml` returns a `Config` with all defaults; no exception.
- **line_tolerance override test** — fixture `code-review.toml` sets `[dedup] line_tolerance = 5`; assert `Config.dedup_line_tolerance == 5`; pass the config to `aggregate()` and assert a near-line pair at distance 4 (which would not merge at default tolerance 3) now merges.
- **severity override test** — fixture overrides one entry; assert the override is reflected in `map_severity` output when the config is active.
- **hotspot_weights override test** — fixture overrides `[hotspots.weights] cyclomatic_complexity = 2.0`; assert the returned `composite_score` is higher for a high-complexity file than with the default weight.
- **malformed TOML test** — fixture with a syntax-error TOML; assert `ConfigError` is raised with a message containing the path.

Green-bar: `pytest tests/test_config.py` passes; mypy strict clean; ruff clean.

## Dependencies

- s2-t1 (aggregator accepts `config`).
- s2-t2 (hotspots accepts `config`).
