---
id: s4-plan
kind: plan
project: code-review
status: active
parent: s4-contract-testing-adapters
created: 2026-05-27
updated: 2026-05-27
---

# s4 — Contract testing adapter (Schemathesis) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Schemathesis analyzer adapter — schema-driven contract testing that runs a generated suite against a live API and flags OpenAPI-spec drift, normalised to SARIF for the s2 aggregator. Story-level-only, `full` review scope, 600s timeout, env-var auth, `$TMPDIR` cache. Plus the cross-cutting infra the adapter needs (scope-restriction enforcement, `[contract_testing]` config, severity-override wiring). **Pact is out of scope (ADR-0008).**

**Architecture:** Schemathesis is a pinned Python dependency (`schemathesis==4.0.10`), so per the architecture doc's subprocess rule it is invoked as a **subprocess** of its own CLI (not imported), and its machine-readable report is normalised to a SARIF shim with `ruleId = "schemathesis.<check>"` (e.g. `schemathesis.response_schema_violation`). Findings are emitted at SARIF `level="error"` so the existing s2 `map_severity()` maps them to `critical` by default; an operator `code-review.toml` `[severity]` override per ruleId can lower that (wired in t0). The adapter follows the `semgrep.py` template: `run_subprocess`, a `tempfile.TemporaryDirectory` for scratch + the `HYPOTHESIS_STORAGE_DIRECTORY` redirect, SARIF normalise + validate, `status`/`error`/`timeout` model. No Docker, no broker, no new native dependency.

**Tech Stack:** `schemathesis==4.0.10` (already pinned + installed). New pins (t0): `fastapi` (**test-fixture-only** — the integration test's drifting API) and its server dep (`uvicorn` or `httpx`-based `TestClient` — confirm in t0). No runtime binary; Schemathesis ships as a console script in the venv.

## ⚠️ Verify-first unknowns (resolve at the top of the owning task; do not assume)

1. **Schemathesis 4.0.10 CLI surface (t1).** Schemathesis 4.x changed its CLI substantially from 3.x. Before writing the adapter, confirm: the run subcommand and invocation (`schemathesis run <spec_url>` vs `st run …`), how to point it at a live base URL vs a spec URL, the machine-readable report flag (JUnit XML vs JSON vs VCS), and the exit-code semantics (clean vs findings vs error). Record the confirmed command in the adapter docstring. `uv run schemathesis --help` / `uv run schemathesis run --help`.
2. **The per-task / story-level timing input (t0).** The CLI today has `--review-scope {lite,standard,full}` (analyzer *depth*) but **no `--scope {per-task,story-level}` timing flag**, and `ReviewRequest.scope` is currently fed the review-scope value. The story's scope-gate AC assumes a timing axis. t0 introduces `--scope {per-task,story-level}` (timing), threads it into `ReviewRequest.scope`, and enforces `scope_restrictions` against it — see t0.

## File structure

**Create:**
- `code_review/adapters/schemathesis_.py` — adapter (trailing `_` to avoid shadowing the `schemathesis` package import, mirroring `cohesion_.py`)
- `tests/test_adapters/test_schemathesis.py`
- `tests/fixtures/schemathesis-target/app.py` — fixture FastAPI app with a deliberate response/spec drift
- `tests/test_scope_restrictions.py` — CLI scope-gate enforcement (t0)

**Modify:**
- `code_review/cli.py` — add `--scope {per-task,story-level}`; enforce `scope_restrictions`; thread `severity_overrides` into aggregation
- `code_review/aggregator.py` — `aggregate()` accepts `severity_overrides`; `_apply_sdlc_severity()` applies per-ruleId override
- `code_review/config.py` — validate `severity_overrides` values ∈ SDLC taxonomy; parse `[contract_testing]` section
- `code_review/adapters/__init__.py` — register `schemathesis` in REGISTRY
- `code_review/capabilities.json` — Schemathesis analyzer entry (scope `full`, timing story-level-only, 600s) (t2)
- `.claude/skills/code-review/SKILL.md` — contract-testing sandbox-domains subsection (t2) *(note: SKILL.md lives under the host skill dir; see ADR-0007 / sandbox write-block caveat — edit may need the documented bypass)*
- `pyproject.toml` + `stack-pins.md` — pin `fastapi` (test extra) (t0)

---

## Task 0: Contract-adapter infrastructure (scope gate, config, severity override)

**Files:**
- Modify: `code_review/cli.py`, `code_review/aggregator.py`, `code_review/config.py`, `pyproject.toml`, `sdlc/docs/architecture/stack-pins.md`
- Create: `tests/test_scope_restrictions.py`
- Extend: `tests/test_severity.py` / `tests/test_config.py`

**Context:** Three independent infra pieces the adapter depends on, no Schemathesis code yet.

1. **Scope-restriction gate.** Add a Typer option `--scope {per-task,story-level}` (default `per-task`). Pass its value as `ReviewRequest.scope`. After the analyzer set is resolved and before fan-out, for each requested analyzer whose `scope_restrictions` is non-empty: if the chosen scope ∉ `scope_restrictions`, exit non-zero with `Error: analyzer '<name>' requires --scope {<allowed>} (got '<scope>')`. (Schemathesis will declare `scope_restrictions = frozenset({"story-level"})` in t1.)
2. **`severity_overrides` wiring.** Thread `config.severity_overrides` (ruleId → SDLC label) into `aggregate(outputs, line_tolerance=…, severity_overrides=…)` → `_apply_sdlc_severity(result, overrides)`: compute `map_severity(...)` as today, then if `result.ruleId` is a key in `overrides`, the override label wins. Validate override **values** at config load: any value ∉ `{critical, important, minor, nit}` raises `ConfigError` (consistent with the existing TOML-parse error boundary).
3. **`[contract_testing]` config + FastAPI pin.** Parse a `[contract_testing]` table in `code-review.toml` into the config (per-target `spec_url`, `base_url`, `auth.token_env`, `timeout_s`), exposed to the adapter via `ReviewRequest.config`. Pin `fastapi` as a test-only dependency in `pyproject.toml` (+ `stack-pins.md` Python dev-deps table); run rule #1b reconciliation (`uv sync`) in the same commit.

- [ ] **Step 1: Write failing tests** — `tests/test_scope_restrictions.py`: (a) `--scope per-task --analyzer schemathesis` → exit 1 + error names `story-level`; (b) `--scope story-level --analyzer schemathesis` accepted (mock the adapter run); (c) an unrestricted analyzer (e.g. `bandit`) is accepted at either scope. Extend `test_severity`/`test_config`: override forces label; absent override → unchanged; invalid override value → `ConfigError`; `[contract_testing]` parses into config.
- [ ] **Step 2: Run tests, confirm they fail** — `uv run pytest tests/test_scope_restrictions.py tests/test_severity.py tests/test_config.py -v`
- [ ] **Step 3: Implement** — the `--scope` option + gate in `cli.py`; `severity_overrides` threading in `aggregator.py`; value validation + `[contract_testing]` parse in `config.py`; `fastapi` pin.
- [ ] **Step 4: Run tests, confirm green**
- [ ] **Step 5: Full suite + lint + types, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add -A
git commit -m "code-review s4-t0: scope-restriction gate, severity-override wiring, [contract_testing] config + fastapi pin"
```

---

## Task 1: Schemathesis adapter + FastAPI fixture + tests

**Files:**
- Create: `code_review/adapters/schemathesis_.py`, `tests/test_adapters/test_schemathesis.py`, `tests/fixtures/schemathesis-target/app.py`
- Modify: `code_review/adapters/__init__.py` (REGISTRY)

**Context:** ⚠️ **Resolve verify-first unknown #1 before writing the adapter.** The adapter (a) reads `spec_url`/`base_url`/`auth.token_env`/`timeout_s` from `request.config["contract_testing"]`, (b) reads the Bearer token from the **named env var** (never from argv) and passes it via Schemathesis's auth flag/header, (c) runs Schemathesis as a subprocess inside a `tempfile.TemporaryDirectory` with `HYPOTHESIS_STORAGE_DIRECTORY` pointed at it (so `.hypothesis/` never lands in CWD), (d) normalises the report → SARIF shim with `ruleId="schemathesis.response_schema_violation"`, `message.text` naming the divergent field, `properties.endpoint`, and `level="error"` (→ `critical`), (e) handles target-unreachable cleanly (`status="error"`, error names the host + `sandbox.allowedDomains` hint), and (f) declares `scope_restrictions = frozenset({"story-level"})`, `default_timeout_s = 600`, no `required_binary` (console script ships in the venv).

- [ ] **Step 0: Confirm the Schemathesis 4.0.10 CLI** — `uv run schemathesis run --help`; record the exact invocation + report flag + exit codes in the adapter docstring.
- [ ] **Step 1: Write failing tests** — protocol conformance (`isinstance(_, Analyzer)`, name, `scope_restrictions`, `default_timeout_s == 600`); unit tests mocking `run_subprocess` for: report→SARIF normalisation (drift → expected ruleId/message/endpoint), unreachable target → `status="error"` naming the host, timeout → `status="timeout"`, token read from env var and **absent from the SARIF/output and from captured argv**; cache-redirect test (set `HOME` to empty tmp dir; assert `HYPOTHESIS_STORAGE_DIRECTORY` is set under `$TMPDIR` and no `.hypothesis/` in CWD/HOME); **skipif-guarded** integration test against the fixture FastAPI app asserting the planted drift surfaces with `schemathesis.response_schema_violation` and the SARIF validates against `sarif-2.1.0.json`.
- [ ] **Step 2: Build the fixture** — `tests/fixtures/schemathesis-target/app.py`: minimal FastAPI app whose OpenAPI declares a field (`user_name`) the handler doesn't return (returns `username`), plus a helper to launch it on an ephemeral port for the integration test (skipif when fastapi/uvicorn unavailable).
- [ ] **Step 3: Run tests, confirm they fail**
- [ ] **Step 4: Implement `SchemathesisAdapter`** (template: `semgrep.py`) + register `"schemathesis"` in `REGISTRY`.
- [ ] **Step 5: Run tests, confirm green** (integration skips if the fixture server can't start)
- [ ] **Step 6: Full suite + lint + types, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add -A
git commit -m "code-review s4-t1: SchemathesisAdapter (subprocess → SARIF), FastAPI drift fixture, env-var auth, \$TMPDIR cache"
```

---

## Task 2: capabilities.json scope assignment + SKILL.md sandbox docs + cross-cutting tests

**Files:**
- Modify: `code_review/capabilities.json`, `.claude/skills/code-review/SKILL.md`
- Create/extend: `tests/test_capabilities.py`, `tests/test_sandbox_compatibility.py`

**Context:** Wire Schemathesis into the static metadata and document the operator-facing sandbox requirement; add the cross-cutting tests that span the adapter + CLI.

- [ ] **Step 1: Write failing tests** — `test_capabilities`: the analyzer registry includes `schemathesis` with `review_scope: full`, timing `story-level-only`, `default_timeout_s: 600`, and the entry validates against the capabilities schema. `test_sandbox_compatibility`: sandbox-blocked-network test — patch the network layer to simulate denial of the configured target; assert the adapter's error message explicitly names `sandbox.allowedDomains`.
- [ ] **Step 2: Run tests, confirm they fail**
- [ ] **Step 3: Implement** — add the Schemathesis entry to `capabilities.json`; add the "Contract testing" subsection to `SKILL.md`'s Sandbox configuration section (per the story's SKILL.md AC — only specific hosts in `allowedDomains`, never wildcards). *(SKILL.md is under the host skill dir; use the documented sandbox-bypass if the write is blocked.)*
- [ ] **Step 4: Run tests, confirm green**
- [ ] **Step 5: Full suite + lint + types, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add -A
git commit -m "code-review s4-t2: capabilities Schemathesis entry, SKILL.md sandbox docs, sandbox-network test"
```

---

## Story close (after t2 closes clean)

- **Story-level Review** on the cumulative s4 diff (per SDLC Review verb): cross-cutting drift, severity-override consistency, error-handling/telemetry across the new CLI paths. Remediate Critical/Important via `-fix<N>` tasks (rule #25, 2-round bound).
- **Supply-chain gate (rule #26):** run the project's dependency audit (covers the new `fastapi` pin) and record the result in the close notes.
- **Acceptance-criteria sweep:** confirm each of the 9 story scenarios has corresponding evidence in the diff before the story moves to `/sdlc/work/done/`.
- **Epic note:** s4 was the last analyzer story; only **s5 (subagent integration)** remains before the epic can close + `document` verb runs.

## Acceptance-criteria → task coverage

| Story scenario | Task |
|---|---|
| Schemathesis runs vs live API → SARIF | t1 |
| Story-level-scope-only gate | t0 (gate) + t1 (declares restriction) |
| Longer timeout budgets (600s, configurable) | t0 (config) + t1 (`default_timeout_s`) |
| Fails cleanly when target unreachable | t1 |
| Findings → `critical` (unless overridden) | t0 (override wiring) + t1 (`level=error`) |
| Auth via env var, never leaked | t1 |
| Only analyzer needing network; sandbox error names `allowedDomains` | t1 (error) + t2 (sandbox test) |
| Hypothesis cache → `$TMPDIR`, never CWD | t1 |
| SKILL.md documents allowlist domains | t2 |
