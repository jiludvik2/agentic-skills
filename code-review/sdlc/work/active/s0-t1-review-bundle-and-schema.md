---
id: s0-t1-review-bundle-and-schema
kind: task
project: code-review
status: active
parent: s0-contract-inversion-and-bundle
sources: [adr-0020-thin-invocation-runner.md]
created: 2026-05-30
updated: 2026-05-30
tags: [bundle, schema, serialization, runner]
---

# Task s0-t1 — ReviewBundle type + JSON serialisation + published schema

## Outcome

A `ReviewBundle` that aggregates the review request echo + per-tool `CaptureOutput`s,
serialises to deterministic JSON, and validates against a published bundle JSON schema —
the contract the agent reads. Additive; the live SARIF emission is untouched (s2 switches
the CLI onto this).

## Design

In `code_review/bundle.py` (the module exists for provisioning; add the bundle type here,
or a new `code_review/review_bundle.py` if cleaner — implementer's call inside the
package):

```python
@dataclass(frozen=True)
class ReviewBundle:
    request: ReviewRequest          # echo: scope, diff_range, target_paths, languages
    outputs: tuple[CaptureOutput, ...]
    def to_dict(self) -> dict[str, Any]: ...   # deterministic, key-ordered

def bundle_to_json(bundle: ReviewBundle) -> str: ...    # stable (sorted keys)
```

- JSON shape (stable, sorted keys):
  ```json
  {
    "schema": "polyreview/review-bundle/v1",
    "request": {"scope": "...", "diff_range": null, "target_paths": ["..."],
                "languages": ["python"]},
    "outputs": [
      {"tool": "bandit", "status": "ok", "exit_code": 0,
       "stdout": "<raw>", "stderr": "", "error": null,
       "command": ["python","-m","bandit","..."], "duration_s": 0.0}
    ]
  }
  ```
- Publish the JSON schema at `code_review/_bundle/schemas/review-bundle.v1.json` (vendored
  like the SARIF schema was) and validate with `jsonschema` (already a dependency).
- `config`/`MetricSet` are **not** referenced; metrics-bearing tools (radon/cohesion/
  pydeps) are treated as ordinary tools whose raw stdout lands in `outputs` (their
  `MetricSet` special-casing is deleted in s1).

## Acceptance criteria

- `ReviewBundle.to_dict()` / `bundle_to_json()` produce **deterministic** output (stable
  key order) carrying the `request` echo and one `outputs` entry per capture with all
  `CaptureOutput` fields.
- A representative bundle (mixed `ok` / `unavailable` / `error` captures across Python +
  JS tools) **validates** against `review-bundle.v1.json`.
- A malformed bundle (missing required field / wrong status enum) **fails** schema
  validation.
- The bundle round-trips: `to_dict()` carries enough to reconstruct the captures' visible
  fields.
- The schema declares the ADR-0019 status enum (`ok|error|timeout|unavailable`) and
  required fields (`tool`, `status`).
- `uv run pytest`, `uv run ruff check .`, `uv run mypy` clean; existing tests still green.

## Test specification (write first, confirm RED)

`tests/test_bundle.py` (new or extended), run via `uv run pytest`:

1. `test_bundle_to_dict_shape` — build a `ReviewBundle` from a `ReviewRequest` + 2–3
   `CaptureOutput`s; assert the dict has `schema`, `request` (with languages as a sorted
   list), and `outputs` with every field present.
2. `test_bundle_json_deterministic` — `bundle_to_json` twice on the same bundle yields
   byte-identical output; keys are sorted.
3. `test_bundle_validates_against_schema` — load
   `review-bundle.v1.json`; a mixed-status bundle validates clean.
4. `test_invalid_bundle_rejected` — a bundle dict with a bogus `status` ("weird") and one
   missing `tool` each raise `jsonschema.ValidationError`.
5. `test_unavailable_capture_in_bundle` — an `unavailable` capture serialises with empty
   stdout + reason in `error` and validates.
6. `test_raw_stdout_roundtrips` — a capture whose stdout is non-JSON text survives
   serialisation unchanged (the agent must receive raw output verbatim).

## Notes

- Depends on s0-t0 (`CaptureOutput`).
- `schema` version string (`v1`) lets the agent/SKILL.md pin the contract; bump on any
  breaking shape change.
- Keep the schema minimal — it constrains structure (fields, status enum), **not** the
  content of `stdout` (which is deliberately opaque/heterogeneous).
