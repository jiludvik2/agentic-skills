---
id: s5-t0-bundle-oracle-module
kind: task
project: code-review
status: active
parent: s5-maintainability-oracle
sources: [s5-maintainability-oracle.md, adr-0020-thin-invocation-runner.md, qa-analyzer-coverage.md]
created: 2026-05-31
updated: 2026-05-31
tags: [qa, oracle, bundle, coupling, test-first]
---

# Task s5-t0 — bundle oracle module + unit tests (the brain)

## Outcome

A pure, importable module that reads a `review-bundle.v1.json` dict and answers, per tool,
"did the planted defect appear in this tool's raw output?" — including the two G5 precision
coupling oracles (pydeps import cycle, depcruiser prod→`__mocks__` edge). All logic is pure
data transformation over the bundle, so it is fully unit-tested with hand-authored snippets
and **no third-party binaries** — the tests-first heart of s5. `run_smoke.py` is untouched
in this task (s5-t1 wires it).

## Files to add / change

1. **New module** `sdlc/docs/qa/analyzer-coverage/bundle_oracle.py` — pure functions:
   - **Bundle accessors:**
     - `output_for(bundle: dict, tool: str) -> dict | None` — return the `outputs[]` entry
       whose `tool == tool`, else `None`.
     - `status_of(bundle: dict, tool: str) -> str` — the entry's `status` (`ok` | `error` |
       `timeout` | `unavailable`), or `"missing"` if absent.
   - **Per-tool native signal extractors** (each takes the tool's raw `stdout` string and
     returns a small result the oracle can assert on — count or structured detail). One per
     harness analyzer; group by output family so it stays small:
     - **SARIF emitters** (semgrep, eslint, jscomplexity) → `count_sarif_results(stdout)`:
       `sum(len(run["results"]) for run in sarif["runs"])`.
     - **Native-JSON finding lists** — bandit (`results[]`), gitleaks (top-level list),
       trivy (`Results[].Vulnerabilities[]`), knip (its JSON issues), jscpd
       (`duplicates[]`/`statistics`) → one small counter each (tolerant of empty/`{}`).
     - **Text emitters** — vulture, cohesion → count non-blank report lines.
     - **radon** (`radon cc --json`) → `max_cc(stdout)`: max `complexity` across all
       per-file function entries.
     - **schemathesis** → failure/finding count from its JSON (loose, as today).
   - **Precision coupling oracles (the G5 headline):**
     - `pydeps_has_cycle(stdout, a, b) -> bool` — parse pydeps' dep-graph JSON (a dict of
       `module -> {imports?, imported_by?, ...}`) and return `True` iff `b in graph[a].imports`
       **and** `a in graph[b].imports` (the mutual back-edge). Module keys are dotted
       (e.g. `cyclepkg.a`); accept the dotted names the fixture will produce. Verified shape
       (planning probe): `{"cyc.a": {"imports": ["cyc", "cyc.b"], ...}, "cyc.b": {"imports":
       ["cyc", "cyc.a"], ...}}`.
     - `depcruiser_has_edge_into(stdout, needle="__mocks__", from_outside=True) -> bool` —
       parse depcruiser's module graph (`{"modules": [{"source": str, "dependencies":
       [{"resolved": str, "circular": bool, ...}]}], ...}`) and return `True` iff some module
       whose `source` is **outside** `needle` has a dependency whose `resolved` path contains
       `needle/`. (The "specific edge": non-mock source → a `__mocks__/` module.) Keep a
       sibling `depcruiser_has_circular(stdout) -> bool` (any `circular: true`) for the
       existing `cycle_a/cycle_b` case's migration.
   - A tiny dataclass/namedtuple `Signal(ok: bool, detail: str)` is fine if it keeps
     `run_smoke.py` tidy, but is optional — plain returns are acceptable. Match the existing
     `(ok, detail)` tuple convention the harness already uses if you keep it.
2. **New test** `tests/test_qa_bundle_oracle.py` — imports `bundle_oracle` (load it by path
   via `importlib`, since it lives outside the package; mirror how any existing test reaches
   non-package code, or add a thin `sys.path` insert scoped to the test). Unit tests over
   hand-authored snippets (no binaries).

## Acceptance criteria

- `bundle_oracle.py` is importable and contains **no** `subprocess`/binary calls and no
  network — pure functions over dicts/strings.
- `output_for` / `status_of` correctly locate a tool's output by name and report its status,
  including `unavailable`/`error`/missing.
- Each per-tool extractor returns the right signal for a representative native snippet and a
  defensible zero for empty/garbage input (no exceptions on malformed stdout — return a
  zero/`False` signal, since a crashing oracle would mask a real tool result).
- **pydeps precision oracle:** `pydeps_has_cycle(graph, "cyclepkg.a", "cyclepkg.b")` is
  `True` for the planted mutual back-edge and `False` when either direction is missing.
- **depcruiser precision oracle:** `depcruiser_has_edge_into(graph, "__mocks__")` is `True`
  for a `src/app.js → __mocks__/service.js` edge and `False` when the only edge is between
  two `__mocks__/` modules (i.e. no *outside* source).
- `uv run pytest tests/test_qa_bundle_oracle.py`, `uv run ruff check .`,
  `uv run mypy code_review` all clean. (mypy's scope is `code_review`; `bundle_oracle.py` is
  outside it, but the test file lives in `tests/` — keep it ruff-clean and type-honest.)

## Test specification (write first, confirm RED)

`tests/test_qa_bundle_oracle.py`, snippets hand-authored (the pydeps one taken verbatim from
the planning probe). Write all RED (module/functions absent) before implementing:

1. **Accessors** — a 2-output bundle dict; assert `output_for` finds each tool and returns
   `None` for an absent one; `status_of` returns the right enum and `"missing"` for absent.
2. **SARIF counter** — a minimal SARIF string (`{"runs":[{"results":[{...}]}]}`) → 1; empty
   runs → 0; non-JSON → 0 (no raise).
3. **Native counters** — one snippet each for bandit/gitleaks/trivy/knip/jscpd → expected
   count; `{}`/`""` → 0.
4. **radon max_cc** — a `radon cc --json` snippet with functions of complexity 3 and 12 →
   `max_cc == 12`.
5. **vulture/cohesion text** — a few "unused …" lines → count > 0; empty → 0.
6. **pydeps cycle (precision)** — the probe graph `{"cyclepkg.a":{"imports":["cyclepkg",
   "cyclepkg.b"]}, "cyclepkg.b":{"imports":["cyclepkg","cyclepkg.a"]}}` → `True`; remove
   `cyclepkg.a` from `b.imports` → `False`.
7. **depcruiser edge-into (precision)** — graph with `modules:[{"source":"src/app.js",
   "dependencies":[{"resolved":"__mocks__/service.js","circular":false}]}]` →
   `depcruiser_has_edge_into(...,"__mocks__") is True`; a graph whose only `__mocks__` edge
   originates *inside* `__mocks__/` → `False`. Also test `depcruiser_has_circular` True/False
   on a `circular:true` snippet (for the migrated `cycle_a/cycle_b` case).

GREEN after `bundle_oracle.py` implements the functions.

## Notes

- ADR-0020: the bundle carries **raw native** output. Do not assume SARIF for tools that
  don't emit it — confirm each extractor against the real captured stdout in s5-t2 (some
  exact shapes, e.g. knip/jscpd/schemathesis JSON, are only confirmable from a provisioned
  run; author the extractor to the documented shape now, tighten in s5-t2 if the capture
  differs). pydeps and SARIF shapes are confirmed (probe + s3/s4).
- Keep the module dependency-free (stdlib `json` only) so it imports cleanly in `tests/`
  without touching the `code_review` package.
- The two precision oracles are the only ones asked to assert a *specific* defect; the rest
  preserve the harness's existing loose `≥1`/`max_cc>=10` semantics — do not over-tighten
  them here.
