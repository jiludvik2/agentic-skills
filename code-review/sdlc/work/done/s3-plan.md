---
id: s3-plan
kind: plan
project: code-review
status: done
parent: s3-remaining-deterministic-adapters
created: 2026-05-27
updated: 2026-05-30
---

# s3 Remaining Deterministic Adapters — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 10 new analyzer adapters (bandit, vulture, pydeps, cohesion, gitleaks, trivy, eslint, jscpd, knip, dependency-cruiser) plus shared infrastructure, per-language auto-selection, and cross-cutting tests.

**Architecture:** Shared SARIF utilities live in `sarif_utils.py`. Python-library adapters use `sys.executable` subprocess; binary adapters declare `required_binary`; JS adapters use vendored `node_modules/.bin/` binaries via `js_base.py`. Non-SARIF-native adapters emit a normalised SARIF shim with `ruleId = "<tool>.<category>"`. Per **ADR-0007**, t0 consolidates `capabilities.json` and all four JSON schemas into the `code_review` package as the single source of truth — every package reader resolves them via `Path(__file__)`, the repo-root `/schemas/` and the skill-dir `capabilities.json` are deleted, and bundling is enforced as wheel package-data. This fixes the wheel-install break (`semgrep.py` reading the repo root) and collapses the three duplicate `_SKILL_DIR` constants.

**Test schema-path convention (post-t0):** the canonical SARIF schema for tests is `<repo_root>/code_review/schemas/sarif-2.1.0.json`. In every test template below, where a path is shown as `Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"` (repo-root `/schemas/`), read it as `Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"`. The repo-root `/schemas/` directory no longer exists after t0.

**Tech Stack:** Python deps already installed: bandit 1.7.10, vulture 2.13, pydeps 1.12.20, cohesion 1.1.0. Binaries (require manual install via `scripts/setup.sh`): gitleaks, trivy, node. Vendored Node.js (require `npm ci` in `scripts/setup.sh`): eslint + @microsoft/eslint-formatter-sarif, jscpd, knip, @dependency-cruiser/cli.

**Scope note:** Three natural milestones, each independently mergeable. If scope must be reduced, defer Milestone C (JS adapters, t8–t10) last.
- **Milestone A (t0–t4):** Shared infrastructure + Python library adapters
- **Milestone B (t5–t7):** Binary security adapters + Semgrep offline fix
- **Milestone C (t8–t11):** JS/TS adapter infrastructure + per-language selection

---

## File structure

**Create:**
- `code_review/adapters/sarif_utils.py` — shared SARIF helpers; `collect_python_files` helper extracted here (was duplicated in radon.py)
- `code_review/capabilities.json` — **moved** from `.claude/skills/code-review/capabilities.json` (ADR-0007)
- `code_review/schemas/sarif-2.1.0.json`, `code_review/schemas/capabilities.json`, `code_review/schemas/review-request.json` — **moved** from repo-root `/schemas/` (ADR-0007); `review-response.json` already in `code_review/schemas/`
- `code_review/adapters/bandit.py`
- `code_review/adapters/vulture.py`
- `code_review/adapters/pydeps.py`
- `code_review/adapters/cohesion_.py` — named with trailing `_` to avoid shadowing the `cohesion` package import
- `code_review/adapters/gitleaks.py`
- `code_review/adapters/trivy.py`
- `code_review/adapters/js_base.py`
- `code_review/adapters/eslint.py`
- `code_review/adapters/jscpd.py`
- `code_review/adapters/knip.py`
- `code_review/adapters/depcruiser.py`
- `code_review/lang_select.py`
- `tests/test_adapters/test_sarif_utils.py`
- `tests/test_adapters/test_bandit.py`
- `tests/test_adapters/test_vulture.py`
- `tests/test_adapters/test_pydeps.py`
- `tests/test_adapters/test_cohesion.py`
- `tests/test_adapters/test_gitleaks.py`
- `tests/test_adapters/test_trivy.py`
- `tests/test_adapters/test_eslint.py`
- `tests/test_adapters/test_jscpd.py`
- `tests/test_adapters/test_knip.py`
- `tests/test_adapters/test_depcruiser.py`
- `tests/test_lang_select.py`
- `tests/test_sandbox_compatibility.py`
- `tests/fixtures/python-with-known-issues/dead.py` — unused function for vulture
- `tests/fixtures/python-with-known-issues/cohesive.py` — class with low cohesion for cohesion adapter
- `tests/fixtures/js-with-known-issues/lib/utils.ts` — TS file with unused export and console.log
- `tests/fixtures/js-with-known-issues/lib/utils_copy.ts` — duplicate code for jscpd
- `tests/fixtures/semgrep-rules/subprocess.yaml` — local Semgrep rule for offline integration test

**Modify:**
- `code_review/adapters/base.py` — add `env` parameter to `run_subprocess`
- `code_review/adapters/semgrep.py` — t0: repoint `_SCHEMA_PATH` to `code_review/schemas/` + import `normalise_sarif` from sarif_utils; t7: offline mode
- `code_review/adapters/radon.py` — use `collect_python_files` from `sarif_utils`
- `code_review/adapters/__init__.py` — add all 10 new adapters to REGISTRY
- `code_review/config.py` — repoint `_load_caps_weights` to package `capabilities.json` + delete module `_SKILL_DIR`; add `disabled_analyzers: list[str]` field; parse from TOML
- `code_review/hotspots.py` — repoint capabilities read to package + delete `_SKILL_DIR`
- `code_review/cli.py` — repoint `_CAPABILITIES_PATH` to package (keep `_SKILL_DIR` only for `code-review.toml`); extend `_probe_analyzer` for `node_tool`; enforce `disabled_analyzers`; add auto-selection via `lang_select`
- `pyproject.toml` — declare `capabilities.json` + `schemas/*.json` as wheel package-data (ADR-0007)
- `.claude/skills/code-review/SKILL.md` — update contract-location wording (contracts are package-bundled, surfaced via `--capabilities`)
- Existing tests reading repo-root `/schemas/`: `test_capabilities.py`, `test_scaffold.py`, `test_adapters/test_radon.py`, `test_adapters/test_semgrep.py`, `test_skill_scaffold.py` — repoint to `code_review/schemas/`

**Delete (ADR-0007):**
- `.claude/skills/code-review/capabilities.json` — `git rm` (now in package)
- repo-root `/schemas/sarif-2.1.0.json`, `/schemas/capabilities.json`, `/schemas/review-request.json`, `/schemas/review-response.json` — `git mv` the first three into the package, `git rm` the `review-response.json` duplicate

---

## Task 0: Shared infrastructure + contract consolidation (ADR-0007)

**Implements ADR-0007.** Establishes `sarif_utils.py` and the `env` subprocess param, then consolidates `capabilities.json` + all four schemas into the `code_review` package as the single source of truth (package-relative reads, repo-root `/schemas/` and skill-dir copy deleted, wheel package-data declared).

**Files:**
- Create: `code_review/adapters/sarif_utils.py`
- Create: `code_review/capabilities.json` (from skill dir)
- Move into `code_review/schemas/`: `sarif-2.1.0.json`, `capabilities.json`, `review-request.json` (from repo-root `/schemas/`)
- Modify: `code_review/adapters/base.py` (env param)
- Modify: `code_review/adapters/radon.py` (collect_python_files import)
- Modify: `code_review/adapters/semgrep.py` (normalise import + `_SCHEMA_PATH` → package)
- Modify: `code_review/config.py` (caps read → package, delete `_SKILL_DIR`)
- Modify: `code_review/hotspots.py` (caps read → package, delete `_SKILL_DIR`)
- Modify: `code_review/cli.py` (`_CAPABILITIES_PATH` → package, keep `_SKILL_DIR` for TOML)
- Modify: `pyproject.toml` (wheel package-data)
- Modify: `.claude/skills/code-review/SKILL.md` (contract-location wording)
- Modify existing tests: `test_capabilities.py`, `test_scaffold.py`, `test_adapters/test_radon.py`, `test_adapters/test_semgrep.py`, `test_skill_scaffold.py`
- Delete: `.claude/skills/code-review/capabilities.json`; repo-root `/schemas/` (after moves)
- Test: `tests/test_adapters/test_sarif_utils.py`

- [ ] **Step 1: Write failing tests for sarif_utils**

```python
# tests/test_adapters/test_sarif_utils.py
from pathlib import Path

from code_review.adapters.sarif_utils import (
    collect_python_files,
    empty_sarif,
    make_location,
    normalise_sarif,
    rel_uri,
)

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"


def test_normalise_sarif_adds_version_and_schema():
    result = normalise_sarif({"runs": []})
    assert result["version"] == "2.1.0"
    assert "$schema" in result
    assert "runs" in result


def test_normalise_sarif_preserves_existing():
    sarif = {"version": "2.1.0", "$schema": "x", "runs": []}
    assert normalise_sarif(sarif) == sarif


def test_empty_sarif_structure():
    s = empty_sarif("mytool", "1.2.3")
    assert s["version"] == "2.1.0"
    runs = s["runs"]
    assert len(runs) == 1
    assert runs[0]["tool"]["driver"]["name"] == "mytool"
    assert runs[0]["tool"]["driver"]["version"] == "1.2.3"
    assert runs[0]["results"] == []


def test_make_location():
    loc = make_location("src/foo.py", 42)
    assert loc["physicalLocation"]["artifactLocation"]["uri"] == "src/foo.py"
    assert loc["physicalLocation"]["region"]["startLine"] == 42


def test_rel_uri_relative_to_cwd(tmp_path):
    child = tmp_path / "sub" / "file.py"
    assert rel_uri(child, tmp_path) == "sub/file.py"


def test_rel_uri_outside_root_returns_str(tmp_path):
    other = Path("/other/path.py")
    result = rel_uri(other, tmp_path)
    assert "other/path.py" in result


def test_collect_python_files():
    files = collect_python_files((str(_FIXTURE),))
    names = [f.name for f in files]
    assert "main.py" in names
    assert "complex.py" in names
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_sarif_utils.py -v
```
Expected: ImportError (module not yet created)

- [ ] **Step 3: Create sarif_utils.py**

```python
# code_review/adapters/sarif_utils.py
from __future__ import annotations

from pathlib import Path
from typing import Any

_SARIF_SCHEMA_URI = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
)


def normalise_sarif(sarif: dict[str, Any]) -> dict[str, Any]:
    if "version" not in sarif:
        sarif = {"version": "2.1.0", **sarif}
    if "$schema" not in sarif:
        sarif = {"$schema": _SARIF_SCHEMA_URI, **sarif}
    return sarif


def empty_sarif(tool_name: str, tool_version: str = "0.0.0") -> dict[str, Any]:
    return {
        "$schema": _SARIF_SCHEMA_URI,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {"name": tool_name, "version": tool_version, "rules": []}
                },
                "results": [],
            }
        ],
    }


def make_location(uri: str, start_line: int = 1) -> dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {"uri": uri},
            "region": {"startLine": start_line},
        }
    }


def rel_uri(path: str | Path, root: str | Path | None = None) -> str:
    """Return path as a string relative to root (CWD if None), or absolute str on failure."""
    p = Path(path)
    base = Path(root) if root is not None else Path.cwd()
    try:
        return str(p.relative_to(base))
    except ValueError:
        return str(p)


def collect_python_files(paths: tuple[str, ...]) -> list[Path]:
    """Collect .py files from a mix of directory and file paths."""
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(p.rglob("*.py"))
        elif p.suffix == ".py" and p.is_file():
            files.append(p)
    return files
```

- [ ] **Step 4: Run tests, confirm they pass**

```bash
uv run pytest tests/test_adapters/test_sarif_utils.py -v
```
Expected: 7 passed

- [ ] **Step 5: Add `env` parameter to `run_subprocess` in base.py**

In `code_review/adapters/base.py`, update the function signature and the `asyncio.create_subprocess_exec` call:

```python
async def run_subprocess(
    *cmd: str,
    timeout_s: float = 60.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> SubprocessResult:
    proc: asyncio.subprocess.Process
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
    except Exception as exc:
        return SubprocessResult(stdout=b"", stderr=b"", returncode=-1, error=str(exc))
    # ... rest unchanged
```

- [ ] **Step 6: Consolidate contracts into the package (ADR-0007)**

Move the three repo-root schemas into the package, copy `capabilities.json` in from the skill dir, and remove the stale duplicates. `review-response.json` is already in `code_review/schemas/`, so the repo-root copy is a duplicate to delete.

```bash
git mv schemas/sarif-2.1.0.json code_review/schemas/sarif-2.1.0.json
git mv schemas/capabilities.json code_review/schemas/capabilities.json
git mv schemas/review-request.json code_review/schemas/review-request.json
git rm schemas/review-response.json        # duplicate; package copy is canonical
cp .claude/skills/code-review/capabilities.json code_review/capabilities.json
git rm .claude/skills/code-review/capabilities.json
git add code_review/capabilities.json
# repo-root /schemas/ should now be empty:
rmdir schemas 2>/dev/null || ls -A schemas
```

- [ ] **Step 7: Repoint every package reader to `Path(__file__)`**

`code_review/cli.py` — change:
```python
_CAPABILITIES_PATH = _SKILL_DIR / "capabilities.json"
```
to (keep `_SKILL_DIR` itself — `load_config(_SKILL_DIR)` at line ~193 still uses it for `code-review.toml`):
```python
_CAPABILITIES_PATH = Path(__file__).resolve().parent / "capabilities.json"
```

`code_review/config.py` — in `_load_caps_weights()` change `caps_path = _SKILL_DIR / "capabilities.json"` to `caps_path = Path(__file__).resolve().parent / "capabilities.json"`, then **delete the module-level `_SKILL_DIR` constant** (line 9) — it is now unused (`load_config` takes `skill_dir` as a parameter for the TOML path).

`code_review/hotspots.py` — change `caps_path = _SKILL_DIR / "capabilities.json"` (line ~25) to `caps_path = Path(__file__).resolve().parent / "capabilities.json"`, then **delete the module-level `_SKILL_DIR` constant** (line 9).

`code_review/adapters/semgrep.py` — change `_SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"` to `_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "sarif-2.1.0.json"` (semgrep.py is in `code_review/adapters/`, so `parent.parent` = `code_review/`).

- [ ] **Step 8: Update radon.py + semgrep.py imports to use sarif_utils**

In `code_review/adapters/radon.py`, delete the local `_collect_python_files` function and add at top:
```python
from code_review.adapters.sarif_utils import collect_python_files as _collect_python_files
```

In `code_review/adapters/semgrep.py`, delete the local `_normalise` function and replace with:
```python
from code_review.adapters.sarif_utils import normalise_sarif as _normalise
```

- [ ] **Step 9: Repoint existing tests to `code_review/schemas/`**

Update these test files to read schemas from the package (`<repo_root>/code_review/schemas/…`):
- `tests/test_capabilities.py:10` — `SCHEMA = REPO_ROOT / "schemas" / "capabilities.json"` → `REPO_ROOT / "code_review" / "schemas" / "capabilities.json"`
- `tests/test_scaffold.py:25` — `REPO_ROOT / "schemas" / "sarif-2.1.0.json"` → `REPO_ROOT / "code_review" / "schemas" / "sarif-2.1.0.json"`
- `tests/test_adapters/test_radon.py:7` — `Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"` → `... / "code_review" / "schemas" / "sarif-2.1.0.json"`
- `tests/test_adapters/test_semgrep.py:11` — same substitution as test_radon.py
- `tests/test_skill_scaffold.py` — its `test_contract_schemas_are_valid_jsonschema` must load the three schemas from `code_review/schemas/`; and `test_skill_md_references_schemas` must match the **new** SKILL.md wording (see Step 10). Adjust both assertions accordingly.

- [ ] **Step 10: Update SKILL.md contract-location wording**

In `.claude/skills/code-review/SKILL.md`, replace the line that reads (line ~25):
> The request and response contracts are described by `schemas/review-request.json` and `schemas/review-response.json`. The full static capability declaration lives in `capabilities.json` and validates against `schemas/capabilities.json`.

with:
> The request/response contracts and capability declaration are bundled inside the `code_review` package (`code_review/schemas/*.json`, `code_review/capabilities.json`) and travel with it on install — they are not separate files in the skill directory. To see the live capability declaration merged with runtime availability, run `python -m code_review.cli --capabilities`.

Then make `tests/test_skill_scaffold.py::test_skill_md_references_schemas` assert against whatever tokens this new wording guarantees (e.g. `code_review/capabilities.json`, `--capabilities`) rather than the old skill-dir-relative paths.

- [ ] **Step 11: Declare schemas + capabilities as wheel package-data**

In `pyproject.toml`, under `[tool.hatch.build.targets.wheel]`, add an `artifacts` key so a non-editable build bundles the JSON (they are committed, so hatchling includes them by default — this makes it explicit and guards against future ignore rules):
```toml
[tool.hatch.build.targets.wheel]
packages = ["code_review"]
artifacts = ["code_review/capabilities.json", "code_review/schemas/*.json"]
```
Verify the wheel carries them:
```bash
uv build --wheel 2>&1 | tail -3
python3 -c "import zipfile,glob; w=sorted(glob.glob('dist/*.whl'))[-1]; print([n for n in zipfile.ZipFile(w).namelist() if n.endswith('.json')])"
```
Expected: the printed list includes `code_review/capabilities.json` and the four `code_review/schemas/*.json`. (If `uv build` is unavailable offline, skip the build check and rely on the committed-files default.)

- [ ] **Step 12: Run full suite + ruff + mypy, confirm green**

```bash
uv run pytest --tb=short -q
uv run ruff check .
uv run mypy --config-file pyproject.toml code_review/
```
Expected: 1 pre-existing Semgrep integration failure (fixed later in t7), everything else green; ruff and mypy clean. Confirm no test still references repo-root `/schemas/`.

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "code-review s3-t0: package-bundle contracts (ADR-0007) + sarif_utils + env param"
```

---

## Task 1: Bandit adapter

**Files:**
- Create: `code_review/adapters/bandit.py`
- Create: `tests/test_adapters/test_bandit.py`

**Context:** `bandit 1.7.10` is already in deps. It does NOT support `--format sarif`; use `--format json` and write a shim. JSON result fields: `test_id` (e.g. `"B404"`), `issue_text`, `filename`, `line_number`, `issue_cwe.id`, `issue_severity` (`"HIGH"/"MEDIUM"/"LOW"`). Exit 0 = no findings; exit 1 = findings found; both are success.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adapters/test_bandit.py
import json
from pathlib import Path

import jsonschema
import pytest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"


def test_bandit_protocol_conformance():
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import Analyzer

    assert isinstance(BanditAdapter(), Analyzer)
    assert BanditAdapter.name == "bandit"


async def test_bandit_empty_target_paths_returns_empty_sarif():
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await BanditAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif.get("runs") == []


async def test_bandit_finds_subprocess_issue():
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await BanditAdapter().run(request)
    assert output.status == "ok"
    results = output.sarif["runs"][0]["results"]
    rule_ids = [r["ruleId"] for r in results]
    assert any("B404" in rid or "B603" in rid or "B602" in rid for rid in rule_ids), \
        f"Expected subprocess-related finding; got: {rule_ids}"


async def test_bandit_sarif_schema_valid():
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await BanditAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_bandit.py -v
```
Expected: ImportError

- [ ] **Step 3: Implement BanditAdapter**

```python
# code_review/adapters/bandit.py
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.sarif_utils import (
    collect_python_files,
    empty_sarif,
    make_location,
    normalise_sarif,
    rel_uri,
)
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    cwd = str(Path.cwd())
    results = []
    for r in data.get("results", []):
        cwe_id = r.get("issue_cwe", {}).get("id")
        taxa = (
            [{"toolComponent": {"name": "cwe"}, "id": str(cwe_id)}] if cwe_id else []
        )
        results.append(
            {
                "ruleId": f"bandit.{r['test_id']}",
                "message": {"text": r["issue_text"]},
                "locations": [make_location(rel_uri(r["filename"], cwd), r["line_number"])],
                "taxa": taxa,
            }
        )
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "bandit", "version": "1.7.10", "rules": []}
                    },
                    "results": results,
                }
            ]
        }
    )


class BanditAdapter:
    name: ClassVar[str] = "bandit"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("bandit", "1.7.10"))
        cmd = (
            sys.executable, "-m", "bandit",
            "--format", "json",
            "-r", *request.target_paths,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="bandit timed out")
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"bandit exited {result.returncode}: {stderr}",
            )
        try:
            data: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
```

- [ ] **Step 4: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_bandit.py -v
```
Expected: 4 passed

- [ ] **Step 5: Full suite + lint**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
```

- [ ] **Step 6: Commit**

```bash
git add code_review/adapters/bandit.py tests/test_adapters/test_bandit.py
git commit -m "code-review s3-t1: BanditAdapter (JSON shim → SARIF)"
```

---

## Task 2: Vulture adapter

**Files:**
- Create: `code_review/adapters/vulture.py`
- Create: `tests/test_adapters/test_vulture.py`
- Create: `tests/fixtures/python-with-known-issues/dead.py`

**Context:** `vulture 2.13` is in deps. Use the Python API: `vulture.Vulture()` → `scavenge([str_paths])` → `get_unused_code()`. Each item has: `.name` (str), `.filename` (str), `.first_lineno` (int), `.typ` (str, e.g. `"function"`), `.confidence` (int, 0-100). No `required_binary` needed (library always available).

- [ ] **Step 1: Create fixture with dead code**

```python
# tests/fixtures/python-with-known-issues/dead.py
def never_called() -> str:
    """This function is intentionally unused for vulture testing."""
    return "dead"


_UNUSED_CONSTANT = 42
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_adapters/test_vulture.py
import json
from pathlib import Path

import jsonschema

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"


def test_vulture_protocol_conformance():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import Analyzer

    assert isinstance(VultureAdapter(), Analyzer)
    assert VultureAdapter.name == "vulture"


async def test_vulture_empty_target_paths():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await VultureAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif.get("runs") == []


async def test_vulture_detects_unused_function():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE / "dead.py"),),
                            languages=frozenset({"python"}), config={})
    output = await VultureAdapter().run(request)
    assert output.status == "ok"
    results = output.sarif["runs"][0]["results"]
    rule_ids = [r["ruleId"] for r in results]
    assert any("vulture.unused-" in rid for rid in rule_ids), \
        f"Expected unused-* finding; got: {rule_ids}"


async def test_vulture_sarif_schema_valid():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await VultureAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
```

- [ ] **Step 3: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_vulture.py -v
```
Expected: ImportError

- [ ] **Step 4: Implement VultureAdapter**

```python
# code_review/adapters/vulture.py
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.sarif_utils import (
    collect_python_files,
    empty_sarif,
    make_location,
    normalise_sarif,
    rel_uri,
)
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(items: list[Any]) -> dict[str, Any]:
    cwd = str(Path.cwd())
    results = [
        {
            "ruleId": f"vulture.unused-{item.typ}",
            "message": {
                "text": f"unused {item.typ} '{item.name}' ({item.confidence}% confidence)"
            },
            "locations": [make_location(rel_uri(item.filename, cwd), item.first_lineno)],
        }
        for item in items
    ]
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "vulture", "version": "2.13", "rules": []}
                    },
                    "results": results,
                }
            ]
        }
    )


class VultureAdapter:
    name: ClassVar[str] = "vulture"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("vulture", "2.13"))
        files = collect_python_files(request.target_paths)
        if not files:
            return AnalyzerOutput(sarif=empty_sarif("vulture", "2.13"))
        import vulture as vulture_mod  # inline import — avoid loading at module level

        v = vulture_mod.Vulture()
        v.scavenge([str(f) for f in files])
        items = list(v.get_unused_code())
        return AnalyzerOutput(sarif=_to_sarif(items))
```

- [ ] **Step 5: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_vulture.py -v
```
Expected: 4 passed

- [ ] **Step 6: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/vulture.py tests/test_adapters/test_vulture.py \
    tests/fixtures/python-with-known-issues/dead.py
git commit -m "code-review s3-t2: VultureAdapter (Python API → SARIF)"
```

---

## Task 3: pydeps adapter

**Files:**
- Create: `code_review/adapters/pydeps.py`
- Create: `tests/test_adapters/test_pydeps.py`

**Context:** `pydeps 1.12.20` is in deps. Use subprocess: `python -m pydeps <package> --show-deps --no-output --noshow`. Output is JSON on stdout: `{module_name: {bacon: int, imports: [str], name: str, path: str|null}}`. Run against a directory containing a Python package. Produces `MetricSet.coupling` (per-module fan-out/fan-in). High fan-out (≥ 10 imports) → SARIF finding.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adapters/test_pydeps.py
import json
from pathlib import Path

import jsonschema

SARIF_SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"
PACKAGE = Path(__file__).parent.parent.parent / "code_review"


def test_pydeps_protocol_conformance():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import Analyzer

    assert isinstance(PydepsAdapter(), Analyzer)
    assert PydepsAdapter.name == "pydeps"


async def test_pydeps_empty_target_paths_returns_empty():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await PydepsAdapter().run(request)
    assert output.status == "ok"
    assert output.metrics is not None
    assert output.metrics.coupling == {}


async def test_pydeps_produces_coupling_metrics():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(PACKAGE),),
                            languages=frozenset({"python"}), config={})
    output = await PydepsAdapter().run(request)
    assert output.status == "ok"
    assert output.metrics is not None
    assert len(output.metrics.coupling) > 0
    # Each entry has fan_out and fan_in
    for entry in output.metrics.coupling.values():
        assert "fan_out" in entry
        assert "fan_in" in entry


async def test_pydeps_sarif_schema_valid():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(PACKAGE),),
                            languages=frozenset({"python"}), config={})
    output = await PydepsAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_pydeps.py -v
```

- [ ] **Step 3: Implement PydepsAdapter**

```python
# code_review/adapters/pydeps.py
from __future__ import annotations

import json
import sys
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.sarif_utils import empty_sarif, normalise_sarif
from code_review.contracts import AnalyzerOutput, MetricSet, ReviewRequest

_HIGH_FAN_OUT_THRESHOLD = 10


def _to_sarif_and_metrics(deps: dict[str, Any]) -> tuple[dict[str, Any], MetricSet]:
    fan_in: dict[str, int] = {k: 0 for k in deps}
    for entry in deps.values():
        for imp in entry.get("imports", []):
            if imp in fan_in:
                fan_in[imp] += 1

    coupling: dict[str, dict[str, Any]] = {}
    results = []
    for mod_name, entry in deps.items():
        imports: list[str] = entry.get("imports", [])
        fo = len(imports)
        fi = fan_in.get(mod_name, 0)
        coupling[mod_name] = {"fan_out": fo, "fan_in": fi, "imports": imports}
        if fo >= _HIGH_FAN_OUT_THRESHOLD:
            results.append(
                {
                    "ruleId": "pydeps.high-fan-out",
                    "message": {
                        "text": f"module '{mod_name}' has fan-out {fo} (threshold {_HIGH_FAN_OUT_THRESHOLD})"
                    },
                    "locations": [],
                }
            )

    sarif = normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "pydeps", "version": "1.12.20", "rules": []}
                    },
                    "results": results,
                }
            ]
        }
    )
    return sarif, MetricSet(per_file={}, per_class={}, coupling=coupling)


class PydepsAdapter:
    name: ClassVar[str] = "pydeps"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(
                sarif=empty_sarif("pydeps", "1.12.20"),
                metrics=MetricSet(per_file={}, per_class={}, coupling={}),
            )
        target = request.target_paths[0]
        cmd = (
            sys.executable, "-m", "pydeps", target,
            "--show-deps", "--no-output", "--noshow",
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="pydeps timed out")
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"pydeps exited {result.returncode}: {stderr}",
            )
        try:
            deps: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        sarif, metrics = _to_sarif_and_metrics(deps)
        return AnalyzerOutput(sarif=sarif, metrics=metrics)
```

- [ ] **Step 4: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_pydeps.py -v
```
Expected: 4 passed

- [ ] **Step 5: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/pydeps.py tests/test_adapters/test_pydeps.py
git commit -m "code-review s3-t3: PydepsAdapter (module coupling metrics + SARIF)"
```

---

## Task 4: Cohesion adapter

**Files:**
- Create: `code_review/adapters/cohesion_.py`
- Create: `tests/test_adapters/test_cohesion.py`
- Create: `tests/fixtures/python-with-known-issues/cohesive.py`

**Context:** `cohesion 1.1.0` is in deps. Use Python API: `from cohesion.module import Module; m = Module.from_file(path); data = m.structure`. `structure` is a `defaultdict` keyed by class name; each value is `{cohesion: float (0-100), lineno: int, col_offset: int, variables: [...], functions: {...}}`. Files with no classes produce an empty `structure`. Low cohesion threshold = 50.0%. Produces `MetricSet.per_class`. Note: file is named `cohesion_.py` (trailing underscore) to avoid shadowing the `cohesion` package.

- [ ] **Step 1: Create fixture with low-cohesion class**

```python
# tests/fixtures/python-with-known-issues/cohesive.py
class LowCohesionService:
    """Intentionally low-cohesion class for testing."""

    def __init__(self) -> None:
        self.x = 1
        self.y = 2

    def get_x(self) -> int:
        return self.x

    def get_y(self) -> int:
        return self.y

    def unrelated_a(self) -> str:
        return "hello"

    def unrelated_b(self) -> str:
        return "world"

    def unrelated_c(self) -> int:
        return 42
```

- [ ] **Step 2: Verify cohesion detects this class**

```bash
uv run python -c "
from cohesion.module import Module
m = Module.from_file('tests/fixtures/python-with-known-issues/cohesive.py')
print(m.structure)
"
```
Expected: `LowCohesionService` with `cohesion` value below 50.0.

- [ ] **Step 3: Write failing tests**

```python
# tests/test_adapters/test_cohesion.py
import json
from pathlib import Path

import jsonschema

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"


def test_cohesion_protocol_conformance():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import Analyzer

    assert isinstance(CohesionAdapter(), Analyzer)
    assert CohesionAdapter.name == "cohesion"


async def test_cohesion_empty_target_paths():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await CohesionAdapter().run(request)
    assert output.status == "ok"
    assert output.metrics is not None
    assert output.metrics.per_class == {}


async def test_cohesion_detects_low_cohesion_class():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE / "cohesive.py"),),
                            languages=frozenset({"python"}), config={})
    output = await CohesionAdapter().run(request)
    assert output.status == "ok"
    results = output.sarif["runs"][0]["results"]
    assert any(r["ruleId"] == "cohesion.low-cohesion" for r in results), \
        f"Expected low-cohesion finding; got: {[r['ruleId'] for r in results]}"


async def test_cohesion_populates_per_class_metrics():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE / "cohesive.py"),),
                            languages=frozenset({"python"}), config={})
    output = await CohesionAdapter().run(request)
    assert output.metrics is not None
    assert len(output.metrics.per_class) > 0
    for entry in output.metrics.per_class.values():
        assert "cohesion" in entry
        assert "lineno" in entry


async def test_cohesion_sarif_schema_valid():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await CohesionAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
```

- [ ] **Step 4: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_cohesion.py -v
```

- [ ] **Step 5: Implement CohesionAdapter**

```python
# code_review/adapters/cohesion_.py
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.sarif_utils import (
    collect_python_files,
    empty_sarif,
    make_location,
    normalise_sarif,
    rel_uri,
)
from code_review.contracts import AnalyzerOutput, MetricSet, ReviewRequest

_LOW_COHESION_THRESHOLD = 50.0


def _analyse_file(path: Path) -> dict[str, dict[str, Any]]:
    try:
        from cohesion.module import Module  # inline — avoids shadowing at module level

        m = Module.from_file(str(path))
        return {
            cls_name: {"cohesion": data["cohesion"], "lineno": data["lineno"]}
            for cls_name, data in m.structure.items()
        }
    except Exception:
        return {}


class CohesionAdapter:
    name: ClassVar[str] = "cohesion"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(
                sarif=empty_sarif("cohesion", "1.1.0"),
                metrics=MetricSet(per_file={}, per_class={}, coupling={}),
            )
        cwd = str(Path.cwd())
        files = collect_python_files(request.target_paths)
        per_class: dict[str, dict[str, Any]] = {}
        results = []

        for f in files:
            for cls_name, info in _analyse_file(f).items():
                key = f"{rel_uri(f, cwd)}::{cls_name}"
                per_class[key] = info
                if info["cohesion"] < _LOW_COHESION_THRESHOLD:
                    results.append(
                        {
                            "ruleId": "cohesion.low-cohesion",
                            "message": {
                                "text": (
                                    f"class '{cls_name}' has cohesion "
                                    f"{info['cohesion']:.1f}% "
                                    f"(threshold {_LOW_COHESION_THRESHOLD:.0f}%)"
                                )
                            },
                            "locations": [make_location(rel_uri(f, cwd), info["lineno"])],
                        }
                    )

        sarif = normalise_sarif(
            {
                "runs": [
                    {
                        "tool": {
                            "driver": {"name": "cohesion", "version": "1.1.0", "rules": []}
                        },
                        "results": results,
                    }
                ]
            }
        )
        return AnalyzerOutput(
            sarif=sarif,
            metrics=MetricSet(per_file={}, per_class=per_class, coupling={}),
        )
```

- [ ] **Step 6: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_cohesion.py -v
```
Expected: 5 passed

- [ ] **Step 7: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/cohesion_.py tests/test_adapters/test_cohesion.py \
    tests/fixtures/python-with-known-issues/cohesive.py
git commit -m "code-review s3-t4: CohesionAdapter (LCOM4 metrics + SARIF)"
```

---

## Task 5: gitleaks adapter

**Files:**
- Create: `code_review/adapters/gitleaks.py`
- Create: `tests/test_adapters/test_gitleaks.py`

**Context:** `gitleaks` is an external binary (not in Python deps). Use `required_binary = "gitleaks"` so `_probe_analyzer` in cli.py handles availability. Command: `gitleaks detect --source <path> --report-format sarif --report-path <cwd-relative-tmp> --no-git --exit-code 0`. Use a CWD-relative temp file for the report (not `/tmp` — sandbox constraint). Integration tests use `@pytest.mark.skipif(shutil.which("gitleaks") is None, ...)`. Unit tests mock subprocess output.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adapters/test_gitleaks.py
import json
import shutil
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

SARIF_SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"


def test_gitleaks_protocol_conformance():
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import Analyzer

    assert isinstance(GitleaksAdapter(), Analyzer)
    assert GitleaksAdapter.name == "gitleaks"
    assert GitleaksAdapter.required_binary == "gitleaks"


async def test_gitleaks_returns_error_when_subprocess_fails():
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(".",), languages=frozenset(), config={})
    with patch(
        "code_review.adapters.gitleaks.run_subprocess",
        return_value=SubprocessResult(b"", b"no binary", -1, error="gitleaks not found"),
    ):
        output = await GitleaksAdapter().run(request)
    assert output.status == "error"


async def test_gitleaks_parses_sarif_from_report_file(tmp_path):
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = {
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "gitleaks"}}, "results": []}],
    }

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        # Write fake SARIF to the tmp file that the adapter created
        for arg in args:
            if str(arg).endswith(".sarif"):
                Path(str(arg)).write_text(json.dumps(fake_sarif))
                break
        return SubprocessResult(b"", b"", 0)

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(".",), languages=frozenset(), config={})
    with patch("code_review.adapters.gitleaks.run_subprocess", new=AsyncMock(side_effect=fake_run)):
        output = await GitleaksAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "gitleaks"


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
async def test_gitleaks_integration_no_secrets(tmp_path):
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    clean_file = tmp_path / "clean.py"
    clean_file.write_text("x = 1\n")
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    output = await GitleaksAdapter().run(request)
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_gitleaks.py -v
```

- [ ] **Step 3: Implement GitleaksAdapter**

```python
# code_review/adapters/gitleaks.py
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.contracts import AnalyzerOutput, ReviewRequest


class GitleaksAdapter:
    name: ClassVar[str] = "gitleaks"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "gitleaks"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        source = request.target_paths[0] if request.target_paths else "."
        tmp_path = Path.cwd() / f".gitleaks-{uuid.uuid4().hex}.sarif"
        cmd = (
            "gitleaks", "detect",
            "--source", source,
            "--report-format", "sarif",
            "--report-path", str(tmp_path),
            "--no-git",
            "--exit-code", "0",
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        try:
            if result.error is not None:
                return AnalyzerOutput(sarif={}, status="error", error=result.error)
            if result.timed_out:
                return AnalyzerOutput(sarif={}, status="timeout", error="gitleaks timed out")
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")
                return AnalyzerOutput(
                    sarif={}, status="error",
                    error=f"gitleaks exited {result.returncode}: {stderr}",
                )
            if not tmp_path.exists():
                return AnalyzerOutput(sarif={}, status="error",
                                      error="gitleaks produced no report file")
            sarif: dict[str, Any] = json.loads(tmp_path.read_text())
            return AnalyzerOutput(sarif=sarif)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
```

- [ ] **Step 4: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_gitleaks.py -v
```
Expected: 3 passed (integration test skipped if gitleaks absent)

- [ ] **Step 5: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/gitleaks.py tests/test_adapters/test_gitleaks.py
git commit -m "code-review s3-t5: GitleaksAdapter (SARIF native, binary)"
```

---

## Task 6: Trivy adapter

**Files:**
- Create: `code_review/adapters/trivy.py`
- Create: `tests/test_adapters/test_trivy.py`

**Context:** `trivy` is an external binary. Cache dir: `.claude/skills/code-review/cache/trivy-db/` (pre-fetched by `setup.sh`). If absent, return `status="error"` with a setup message. Flags: `trivy fs --format sarif --output <tmp> --cache-dir <cache> --skip-db-update --offline-scan <source>`. Report written to a CWD-relative temp file.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adapters/test_trivy.py
import json
import shutil
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

SARIF_SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"


def test_trivy_protocol_conformance():
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import Analyzer

    assert isinstance(TrivyAdapter(), Analyzer)
    assert TrivyAdapter.name == "trivy"
    assert TrivyAdapter.required_binary == "trivy"


async def test_trivy_returns_error_when_cache_absent(tmp_path):
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    with patch("code_review.adapters.trivy._TRIVY_CACHE_DIR", tmp_path / "nonexistent"):
        output = await TrivyAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_trivy_parses_sarif_from_report_file(tmp_path):
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = {
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "trivy"}}, "results": []}],
    }

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        for arg in args:
            if "--output" in str(args):
                idx = list(args).index("--output")
                Path(str(args[idx + 1])).write_text(json.dumps(fake_sarif))
                break
        return SubprocessResult(b"", b"", 0)

    cache_dir = tmp_path / "trivy-db"
    cache_dir.mkdir()
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    with (
        patch("code_review.adapters.trivy._TRIVY_CACHE_DIR", cache_dir),
        patch("code_review.adapters.trivy.run_subprocess", new=AsyncMock(side_effect=fake_run)),
    ):
        output = await TrivyAdapter().run(request)
    assert output.status == "ok"


@pytest.mark.skipif(shutil.which("trivy") is None, reason="trivy not installed")
async def test_trivy_integration(tmp_path):
    from code_review.adapters.trivy import TrivyAdapter, _TRIVY_CACHE_DIR
    from code_review.contracts import ReviewRequest

    if not _TRIVY_CACHE_DIR.exists():
        pytest.skip("trivy DB not pre-fetched (run scripts/setup.sh)")
    clean_file = tmp_path / "main.py"
    clean_file.write_text("x = 1\n")
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    output = await TrivyAdapter().run(request)
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_trivy.py -v
```

- [ ] **Step 3: Implement TrivyAdapter**

```python
# code_review/adapters/trivy.py
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.contracts import AnalyzerOutput, ReviewRequest

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "skills" / "code-review"
_TRIVY_CACHE_DIR = _SKILL_DIR / "cache" / "trivy-db"


class TrivyAdapter:
    name: ClassVar[str] = "trivy"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 180
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    required_binary: ClassVar[str] = "trivy"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not _TRIVY_CACHE_DIR.exists():
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"Trivy DB not pre-fetched. Run scripts/setup.sh. Expected: {_TRIVY_CACHE_DIR}",
            )
        source = request.target_paths[0] if request.target_paths else "."
        tmp_path = Path.cwd() / f".trivy-{uuid.uuid4().hex}.sarif"
        cmd = (
            "trivy", "fs",
            "--format", "sarif",
            "--output", str(tmp_path),
            "--cache-dir", str(_TRIVY_CACHE_DIR),
            "--skip-db-update",
            "--offline-scan",
            source,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        try:
            if result.error is not None:
                return AnalyzerOutput(sarif={}, status="error", error=result.error)
            if result.timed_out:
                return AnalyzerOutput(sarif={}, status="timeout", error="trivy timed out")
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")
                return AnalyzerOutput(
                    sarif={}, status="error",
                    error=f"trivy exited {result.returncode}: {stderr}",
                )
            if not tmp_path.exists():
                return AnalyzerOutput(sarif={}, status="error",
                                      error="trivy produced no output file")
            sarif: dict[str, Any] = json.loads(tmp_path.read_text())
            return AnalyzerOutput(sarif=sarif)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
```

- [ ] **Step 4: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_trivy.py -v
```

- [ ] **Step 5: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/trivy.py tests/test_adapters/test_trivy.py
git commit -m "code-review s3-t6: TrivyAdapter (offline SARIF, binary)"
```

---

## Task 7: Semgrep offline fix

**Files:**
- Modify: `code_review/adapters/semgrep.py`
- Modify: `tests/test_adapters/test_semgrep.py`
- Create: `tests/fixtures/semgrep-rules/subprocess.yaml`

**Context:** `test_semgrep_produces_valid_sarif` currently fails because `--config auto` fetches from the Semgrep registry and returns empty results. Fix: add `SEMGREP_USER_DATA_FOLDER` env var (keeps semgrep writes inside CWD); fall back to local rule path when `cache/semgrep/rules/` is present; use `--metrics off`. For the integration test, create a minimal local rule file and use it as config.

- [ ] **Step 1: Create local semgrep rule fixture**

```yaml
# tests/fixtures/semgrep-rules/subprocess.yaml
rules:
  - id: subprocess-shell-true
    patterns:
      - pattern: subprocess.run(..., shell=True, ...)
    message: >
      subprocess.run with shell=True is a security risk (CWE-78).
    languages: [python]
    severity: WARNING
    metadata:
      cwe: "CWE-78"
```

- [ ] **Step 2: Verify the rule works locally**

```bash
uv run semgrep --config tests/fixtures/semgrep-rules/subprocess.yaml \
    tests/fixtures/python-with-known-issues/main.py --json 2>&1 | python3 -m json.tool | head -20
```
Expected: JSON with a `subprocess-shell-true` finding in `main.py`.

- [ ] **Step 3: Update test to use local rules**

In `tests/test_adapters/test_semgrep.py`, update `test_semgrep_produces_valid_sarif` to pass `config={"semgrep_rules": str(RULES_PATH)}` in the ReviewRequest and update the adapter to read it:

```python
RULES_PATH = Path(__file__).parent.parent / "fixtures" / "semgrep-rules"

async def test_semgrep_produces_valid_sarif():
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE_PATH),),
        languages=frozenset({"python"}),
        config={"semgrep_rules": str(RULES_PATH)},
    )
    output = await SemgrepAdapter().run(request)

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(output.sarif, schema)

    results = output.sarif.get("runs", [{}])[0].get("results", [])
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("subprocess-shell-true" in rid for rid in rule_ids), (
        f"Expected subprocess-shell-true finding; got rule IDs: {rule_ids}"
    )
```

- [ ] **Step 4: Run test, confirm it now fails for the right reason (adapter doesn't read config yet)**

```bash
uv run pytest tests/test_adapters/test_semgrep.py::test_semgrep_produces_valid_sarif -v
```

- [ ] **Step 5: Update semgrep.py to use env var + config-supplied rules + --metrics off**

Replace the current `run` method body:

```python
import os

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "skills" / "code-review"
_DEFAULT_RULES = _SKILL_DIR / "cache" / "semgrep" / "rules"
_USER_DATA_DIR = Path.cwd() / ".cache" / "semgrep"


class SemgrepAdapter:
    # ... class vars unchanged ...

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        if not request.target_paths:
            return AnalyzerOutput(sarif=_normalise({"runs": []}))

        # Resolve rules: config-supplied path → local pre-fetched cache → auto (network)
        rules_override: str | None = request.config.get("semgrep_rules")
        if rules_override and Path(rules_override).exists():
            config_arg = rules_override
        elif _DEFAULT_RULES.is_dir():
            config_arg = str(_DEFAULT_RULES)
        else:
            config_arg = "auto"

        user_data_dir = _USER_DATA_DIR
        user_data_dir.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "SEMGREP_USER_DATA_FOLDER": str(user_data_dir)}

        cmd = (
            "semgrep", "--sarif",
            "--config", config_arg,
            "--metrics", "off",
            *request.target_paths,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s, env=env)
        # ... rest of error handling unchanged ...
```

Also add `import os` at the top of semgrep.py.

- [ ] **Step 6: Run integration test, confirm it passes**

```bash
uv run pytest tests/test_adapters/test_semgrep.py -v
```
Expected: all tests pass (including `test_semgrep_produces_valid_sarif`)

- [ ] **Step 7: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/semgrep.py tests/test_adapters/test_semgrep.py \
    tests/fixtures/semgrep-rules/subprocess.yaml
git commit -m "code-review s3-t7: Semgrep offline fix (local rules, SEMGREP_USER_DATA_FOLDER)"
```

---

## Task 8: JS adapter infrastructure

**Files:**
- Create: `code_review/adapters/js_base.py`
- Modify: `code_review/cli.py` (`_probe_analyzer` extension)
- Create: `tests/fixtures/js-with-known-issues/lib/utils.ts`
- Create: `tests/fixtures/js-with-known-issues/lib/utils_copy.ts`

**Context:** JS adapters use vendored binaries in `.claude/skills/code-review/node_modules/.bin/`. Reads are allowed from that path (sandbox only blocks writes). `node` must be on PATH. Each JS adapter class carries `node_tool: ClassVar[str] = "<tool-name>"` instead of `required_binary`.

- [ ] **Step 1: Write failing tests for js_base**

```python
# tests/test_adapters/test_js_base.py  (add this file)
import shutil
from pathlib import Path
from unittest.mock import patch


def test_node_binary_returns_none_when_not_installed(tmp_path):
    from code_review.adapters.js_base import node_binary

    with patch("code_review.adapters.js_base._NODE_MODULES", tmp_path / "node_modules"):
        result = node_binary("eslint")
    assert result is None


def test_node_binary_returns_path_when_present(tmp_path):
    from code_review.adapters.js_base import node_binary

    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    fake = bin_dir / "eslint"
    fake.touch()
    with patch("code_review.adapters.js_base._NODE_MODULES", tmp_path / "node_modules"):
        result = node_binary("eslint")
    assert result == fake


def test_probe_js_adapter_unavailable_no_node_modules(tmp_path):
    from code_review.adapters.js_base import probe_js_adapter

    with patch("code_review.adapters.js_base._NODE_MODULES", tmp_path / "node_modules"):
        probe = probe_js_adapter("eslint")
    assert probe["status"] == "unavailable"
    assert "setup.sh" in probe["error"]


def test_probe_js_adapter_available_when_binary_present(tmp_path):
    import shutil

    from code_review.adapters.js_base import probe_js_adapter

    if shutil.which("node") is None:
        import pytest
        pytest.skip("node not on PATH")
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "eslint").touch()
    with patch("code_review.adapters.js_base._NODE_MODULES", tmp_path / "node_modules"):
        probe = probe_js_adapter("eslint")
    assert probe["status"] == "available"
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_js_base.py -v
```

- [ ] **Step 3: Create js_base.py**

```python
# code_review/adapters/js_base.py
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "skills" / "code-review"
_NODE_MODULES = _SKILL_DIR / "node_modules"


def node_binary(tool: str) -> Path | None:
    """Return path to vendored Node.js binary, or None if not installed."""
    candidate = _NODE_MODULES / ".bin" / tool
    return candidate if candidate.exists() else None


def probe_js_adapter(tool: str) -> dict[str, Any]:
    """Return capabilities probe dict for a JS/Node.js adapter."""
    if shutil.which("node") is None:
        return {"status": "unavailable", "error": "node not found on PATH"}
    binary = node_binary(tool)
    if binary is None:
        return {
            "status": "unavailable",
            "error": f"{tool} not in {_NODE_MODULES / '.bin'}. Run scripts/setup.sh first.",
        }
    return {"status": "available", "error": None}
```

- [ ] **Step 4: Extend `_probe_analyzer` in cli.py**

Find `_probe_analyzer` in `code_review/cli.py` and update it:

```python
def _probe_analyzer(adapter_cls: type[Any]) -> dict[str, Any]:
    node_tool = getattr(adapter_cls, "node_tool", None)
    if node_tool is not None:
        from code_review.adapters.js_base import probe_js_adapter
        return probe_js_adapter(str(node_tool))
    binary = getattr(adapter_cls, "required_binary", None)
    if binary is None:
        return {"status": "available", "error": None}
    if shutil.which(binary) is None:
        return {"status": "unavailable", "error": f"{binary} not found on PATH"}
    return {"status": "available", "error": None}
```

- [ ] **Step 5: Create JS fixtures**

```typescript
// tests/fixtures/js-with-known-issues/lib/utils.ts
export const unusedExport = "this is never imported anywhere";

export function formatDate(date: Date): string {
  console.log("formatting"); // intentional console.log for ESLint
  return date.toISOString().split("T")[0];
}

export function add(a: number, b: number): number {
  return a + b;
}
```

```typescript
// tests/fixtures/js-with-known-issues/lib/utils_copy.ts
// Intentional duplicate of utils.ts for jscpd detection
export const unusedExport2 = "this is never imported anywhere";

export function formatDate2(date: Date): string {
  console.log("formatting");
  return date.toISOString().split("T")[0];
}

export function add2(a: number, b: number): number {
  return a + b;
}
```

- [ ] **Step 6: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_js_base.py -v
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
```

- [ ] **Step 7: Commit**

```bash
git add code_review/adapters/js_base.py code_review/cli.py \
    tests/test_adapters/test_js_base.py \
    tests/fixtures/js-with-known-issues/
git commit -m "code-review s3-t8: JS adapter infrastructure (js_base.py, probe extension, fixtures)"
```

---

## Task 9: ESLint adapter

**Files:**
- Create: `code_review/adapters/eslint.py`
- Create: `tests/test_adapters/test_eslint.py`

**Context:** ESLint emits SARIF via `@microsoft/eslint-formatter-sarif`. The formatter is a node module; reference it by package name (eslint resolves from the same `node_modules`). Command: `node .../eslint --format @microsoft/eslint-formatter-sarif <paths>`. Skip with `skipif` when node_modules absent. Unit tests mock `run_subprocess`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adapters/test_eslint.py
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "sarif-2.1.0.json"


def test_eslint_protocol_conformance():
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import Analyzer

    assert isinstance(EslintAdapter(), Analyzer)
    assert EslintAdapter.name == "eslint"
    assert EslintAdapter.node_tool == "eslint"


async def test_eslint_returns_error_when_binary_absent(tmp_path):
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    with patch("code_review.adapters.eslint.node_binary", return_value=None):
        request = ReviewRequest(scope="per-task", diff_range=None,
                                target_paths=(str(tmp_path),),
                                languages=frozenset(), config={})
        output = await EslintAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_eslint_empty_target_paths():
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    with patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")):
        output = await EslintAdapter().run(request)
    assert output.status == "ok"


async def test_eslint_parses_sarif_stdout():
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = json.dumps({
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "ESLint"}}, "results": []}],
    }).encode()

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=("src/",), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess",
              new=AsyncMock(return_value=SubprocessResult(fake_sarif, b"", 0))),
    ):
        output = await EslintAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "ESLint"
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
uv run pytest tests/test_adapters/test_eslint.py -v
```

- [ ] **Step 3: Implement EslintAdapter**

```python
# code_review/adapters/eslint.py
from __future__ import annotations

import json
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import node_binary, probe_js_adapter
from code_review.adapters.sarif_utils import empty_sarif, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest


class EslintAdapter:
    name: ClassVar[str] = "eslint"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 90
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "eslint"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("eslint")
        if binary is None:
            probe = probe_js_adapter("eslint")
            return AnalyzerOutput(sarif={}, status="error", error=probe["error"])
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("eslint"))
        cmd = (
            "node", str(binary),
            "--format", "@microsoft/eslint-formatter-sarif",
            *request.target_paths,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="eslint timed out")
        # ESLint exits 0 (no findings), 1 (findings), 2 (error) — 0 and 1 are success
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"eslint exited {result.returncode}: {stderr}",
            )
        try:
            sarif: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=normalise_sarif(sarif))
```

- [ ] **Step 4: Run tests, confirm green**

```bash
uv run pytest tests/test_adapters/test_eslint.py -v
```
Expected: 4 passed

- [ ] **Step 5: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/eslint.py tests/test_adapters/test_eslint.py
git commit -m "code-review s3-t9: EslintAdapter (vendored binary, SARIF formatter)"
```

---

## Task 10: jscpd, knip, dependency-cruiser adapters

**Files:**
- Create: `code_review/adapters/jscpd.py`
- Create: `code_review/adapters/knip.py`
- Create: `code_review/adapters/depcruiser.py`
- Create: `tests/test_adapters/test_jscpd.py`
- Create: `tests/test_adapters/test_knip.py`
- Create: `tests/test_adapters/test_depcruiser.py`

**Context:** All three emit JSON → SARIF shim. `jscpd --reporters json` outputs duplication data; `knip --reporter json` outputs unused exports/files/deps; `depcruise --output-type json` outputs dependency graph. Each uses `node_tool` classvar. Unit tests mock subprocess; integration tests use `skipif`.

**jscpd JSON shape** (key fields): `statistics.total.duplicatedLines`, `duplicates[].firstFile.name`, `duplicates[].secondFile.name`, `duplicates[].firstFile.start`

**knip JSON shape**: `{files: [str], exports: [{file, symbol}], dependencies: [{name}]}`

**depcruiser JSON shape**: `{modules: [{source, dependencies: [{resolved, circular}]}]}`

- [ ] **Step 1: Implement jscpd.py**

```python
# code_review/adapters/jscpd.py
from __future__ import annotations

import json
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import node_binary, probe_js_adapter
from code_review.adapters.sarif_utils import empty_sarif, make_location, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for dup in data.get("duplicates", []):
        first = dup.get("firstFile", {})
        second = dup.get("secondFile", {})
        results.append(
            {
                "ruleId": "jscpd.duplicate-code",
                "message": {
                    "text": (
                        f"Duplicate code block: {first.get('name', '?')} "
                        f"and {second.get('name', '?')}"
                    )
                },
                "locations": [
                    make_location(first.get("name", "unknown"), first.get("start", 1))
                ],
                "relatedLocations": [
                    {
                        "id": 1,
                        "message": {"text": "Duplicate location"},
                        "physicalLocation": {
                            "artifactLocation": {"uri": second.get("name", "unknown")},
                            "region": {"startLine": second.get("start", 1)},
                        },
                    }
                ],
            }
        )
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {"driver": {"name": "jscpd", "version": "4.0.5", "rules": []}},
                    "results": results,
                }
            ]
        }
    )


class JscpdAdapter:
    name: ClassVar[str] = "jscpd"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 60
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "jscpd"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("jscpd")
        if binary is None:
            probe = probe_js_adapter("jscpd")
            return AnalyzerOutput(sarif={}, status="error", error=probe["error"])
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("jscpd"))
        cmd = (
            "node", str(binary),
            "--reporters", "json",
            "--output", "/dev/stdout",
            *request.target_paths,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="jscpd timed out")
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"jscpd exited {result.returncode}: {stderr}",
            )
        try:
            data: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
```

- [ ] **Step 2: Implement knip.py**

```python
# code_review/adapters/knip.py
from __future__ import annotations

import json
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import node_binary, probe_js_adapter
from code_review.adapters.sarif_utils import empty_sarif, make_location, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for filepath in data.get("files", []):
        results.append(
            {
                "ruleId": "knip.unused-file",
                "message": {"text": f"Unused file: {filepath}"},
                "locations": [make_location(filepath, 1)],
            }
        )
    for export in data.get("exports", []):
        results.append(
            {
                "ruleId": "knip.unused-export",
                "message": {"text": f"Unused export '{export.get('symbol', '?')}' in {export.get('file', '?')}"},
                "locations": [make_location(export.get("file", "unknown"), 1)],
            }
        )
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {"driver": {"name": "knip", "version": "5.0.0", "rules": []}},
                    "results": results,
                }
            ]
        }
    )


class KnipAdapter:
    name: ClassVar[str] = "knip"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 120
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "knip"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("knip")
        if binary is None:
            probe = probe_js_adapter("knip")
            return AnalyzerOutput(sarif={}, status="error", error=probe["error"])
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("knip"))
        cmd = ("node", str(binary), "--reporter", "json")
        result = await run_subprocess(
            *cmd, timeout_s=self.default_timeout_s, cwd=request.target_paths[0]
        )
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="knip timed out")
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"knip exited {result.returncode}: {stderr}",
            )
        try:
            data: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
```

- [ ] **Step 3: Implement depcruiser.py**

```python
# code_review/adapters/depcruiser.py
from __future__ import annotations

import json
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import node_binary, probe_js_adapter
from code_review.adapters.sarif_utils import empty_sarif, make_location, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest


def _to_sarif(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for module in data.get("modules", []):
        source = module.get("source", "unknown")
        for dep in module.get("dependencies", []):
            if dep.get("circular", False):
                results.append(
                    {
                        "ruleId": "depcruiser.circular-dependency",
                        "message": {
                            "text": f"Circular dependency: {source} → {dep.get('resolved', '?')}"
                        },
                        "locations": [make_location(source, 1)],
                    }
                )
    return normalise_sarif(
        {
            "runs": [
                {
                    "tool": {
                        "driver": {"name": "dependency-cruiser", "version": "16.0.0", "rules": []}
                    },
                    "results": results,
                }
            ]
        }
    )


class DependencyCruiserAdapter:
    name: ClassVar[str] = "depcruiser"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 90
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "depcruise"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("depcruise")
        if binary is None:
            probe = probe_js_adapter("depcruise")
            return AnalyzerOutput(sarif={}, status="error", error=probe["error"])
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("dependency-cruiser"))
        cmd = (
            "node", str(binary),
            "--output-type", "json",
            *request.target_paths,
        )
        result = await run_subprocess(*cmd, timeout_s=self.default_timeout_s)
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="depcruise timed out")
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"depcruise exited {result.returncode}: {stderr}",
            )
        try:
            data: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=_to_sarif(data))
```

- [ ] **Step 4: Write and run tests for all three (follow bandit/gitleaks pattern — protocol conformance, error-when-binary-absent, mock-subprocess parse)**

For brevity the test files follow the same structure as `test_gitleaks.py`: protocol conformance + binary-absent error + subprocess-mocked parse test. Refer to that file and adapt `tool_name`, `node_tool`, adapter class, and expected SARIF shape.

```bash
uv run pytest tests/test_adapters/test_jscpd.py tests/test_adapters/test_knip.py \
    tests/test_adapters/test_depcruiser.py -v
```
Expected: all pass

- [ ] **Step 5: Full suite + lint, commit**

```bash
uv run pytest --tb=short -q && uv run ruff check . && uv run mypy --config-file pyproject.toml code_review/
git add code_review/adapters/jscpd.py code_review/adapters/knip.py \
    code_review/adapters/depcruiser.py \
    tests/test_adapters/test_jscpd.py tests/test_adapters/test_knip.py \
    tests/test_adapters/test_depcruiser.py
git commit -m "code-review s3-t10: jscpd, knip, dependency-cruiser adapters (JSON→SARIF)"
```

---

## Task 11: REGISTRY wiring, per-language selection, capabilities.json, cross-cutting tests

**Files:**
- Create: `code_review/lang_select.py`
- Create: `tests/test_lang_select.py`
- Create: `tests/test_sandbox_compatibility.py`
- Modify: `code_review/adapters/__init__.py`
- Modify: `code_review/capabilities.json`
- Modify: `code_review/config.py` (add `disabled_analyzers`)
- Modify: `code_review/cli.py` (enforce disabled list, wire lang_select)
- Modify: `tests/test_config.py` (add disabled_analyzers test)

- [ ] **Step 1: Wire all new adapters into REGISTRY**

In `code_review/adapters/__init__.py`:

```python
from code_review.adapters.bandit import BanditAdapter
from code_review.adapters.cohesion_ import CohesionAdapter
from code_review.adapters.depcruiser import DependencyCruiserAdapter
from code_review.adapters.eslint import EslintAdapter
from code_review.adapters.gitleaks import GitleaksAdapter
from code_review.adapters.jscpd import JscpdAdapter
from code_review.adapters.knip import KnipAdapter
from code_review.adapters.pydeps import PydepsAdapter
from code_review.adapters.radon import RadonAdapter
from code_review.adapters.semgrep import SemgrepAdapter
from code_review.adapters.trivy import TrivyAdapter
from code_review.adapters.vulture import VultureAdapter

REGISTRY: dict[str, type[Any]] = {
    "bandit": BanditAdapter,
    "cohesion": CohesionAdapter,
    "depcruiser": DependencyCruiserAdapter,
    "eslint": EslintAdapter,
    "gitleaks": GitleaksAdapter,
    "jscpd": JscpdAdapter,
    "knip": KnipAdapter,
    "pydeps": PydepsAdapter,
    "radon": RadonAdapter,
    "semgrep": SemgrepAdapter,
    "trivy": TrivyAdapter,
    "vulture": VultureAdapter,
}
```

- [ ] **Step 2: Update capabilities.json with all new adapters**

Add to the `"analyzers"` array in `code_review/capabilities.json`:

```json
{"id": "bandit", "kind": "deterministic", "languages": ["python"], "rule_classes": ["security"], "taxonomies_tagged": ["cwe"], "default_timeout_s": 60, "scope_restriction": null},
{"id": "vulture", "kind": "deterministic", "languages": ["python"], "rule_classes": ["dead-code"], "taxonomies_tagged": [], "default_timeout_s": 60, "scope_restriction": null},
{"id": "pydeps", "kind": "deterministic", "languages": ["python"], "rule_classes": ["coupling"], "taxonomies_tagged": [], "default_timeout_s": 120, "scope_restriction": null},
{"id": "cohesion", "kind": "deterministic", "languages": ["python"], "rule_classes": ["cohesion"], "taxonomies_tagged": [], "default_timeout_s": 60, "scope_restriction": null},
{"id": "gitleaks", "kind": "deterministic", "languages": ["python", "javascript", "typescript"], "rule_classes": ["secrets"], "taxonomies_tagged": [], "default_timeout_s": 60, "scope_restriction": null},
{"id": "trivy", "kind": "deterministic", "languages": ["python", "javascript", "typescript"], "rule_classes": ["security", "dependency"], "taxonomies_tagged": ["cve"], "default_timeout_s": 180, "scope_restriction": null},
{"id": "eslint", "kind": "deterministic", "languages": ["javascript", "typescript"], "rule_classes": ["quality", "security"], "taxonomies_tagged": [], "default_timeout_s": 90, "scope_restriction": null},
{"id": "jscpd", "kind": "deterministic", "languages": ["javascript", "typescript"], "rule_classes": ["duplication"], "taxonomies_tagged": [], "default_timeout_s": 60, "scope_restriction": null},
{"id": "knip", "kind": "deterministic", "languages": ["javascript", "typescript"], "rule_classes": ["dead-code"], "taxonomies_tagged": [], "default_timeout_s": 120, "scope_restriction": null},
{"id": "depcruiser", "kind": "deterministic", "languages": ["javascript", "typescript"], "rule_classes": ["coupling"], "taxonomies_tagged": [], "default_timeout_s": 90, "scope_restriction": null}
```

Also update `stack_coverage.python.analyzer_classes` to include `"security"`, `"dead-code"`, `"coupling"`, `"cohesion"` and set `stack_coverage.typescript.status` to `"verified"`.

- [ ] **Step 3: Write failing tests for lang_select**

```python
# tests/test_lang_select.py


def test_python_only_selects_python_adapters():
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"python"}))
    assert "bandit" in result
    assert "vulture" in result
    assert "radon" in result
    assert "eslint" not in result
    assert "knip" not in result


def test_typescript_selects_js_adapters():
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"typescript"}))
    assert "eslint" in result
    assert "jscpd" in result
    assert "bandit" not in result
    assert "radon" not in result


def test_mixed_selects_all_relevant():
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"python", "typescript"}))
    assert "bandit" in result
    assert "eslint" in result
    assert "gitleaks" in result  # language-agnostic


def test_unknown_language_returns_common_only():
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"rust"}))
    assert "gitleaks" in result
    assert "bandit" not in result
    assert "eslint" not in result
```

- [ ] **Step 4: Implement lang_select.py**

```python
# code_review/lang_select.py
from __future__ import annotations

_PYTHON_ADAPTERS = frozenset({"bandit", "vulture", "pydeps", "cohesion", "radon", "semgrep"})
_JS_ADAPTERS = frozenset({"eslint", "jscpd", "knip", "depcruiser"})
_COMMON_ADAPTERS = frozenset({"gitleaks", "trivy"})


def select_adapters(languages: frozenset[str]) -> list[str]:
    """Return the default adapter list for the given language set."""
    selected: set[str] = set(_COMMON_ADAPTERS)
    if "python" in languages:
        selected |= _PYTHON_ADAPTERS
    if "javascript" in languages or "typescript" in languages:
        selected |= _JS_ADAPTERS
    return sorted(selected)
```

- [ ] **Step 5: Run lang_select tests, confirm green**

```bash
uv run pytest tests/test_lang_select.py -v
```
Expected: 4 passed

- [ ] **Step 6: Add `disabled_analyzers` to Config and load_config**

In `code_review/config.py`, add field to Config:

```python
@dataclass
class Config:
    dedup_line_tolerance: int = _DEFAULT_DEDUP_TOLERANCE
    severity_overrides: dict[str, str] = field(default_factory=dict)
    hotspot_weights: dict[str, float] = field(default_factory=_load_caps_weights)
    disabled_analyzers: list[str] = field(default_factory=list)
```

In `load_config`, add after the existing field extractions:

```python
disabled_analyzers: list[str] = [
    str(x) for x in raw.get("disabled_analyzers", [])
]
```

And include in the returned `Config(...)` call:
```python
return Config(
    dedup_line_tolerance=dedup_tolerance,
    severity_overrides=severity_overrides,
    hotspot_weights=hotspot_weights,
    disabled_analyzers=disabled_analyzers,
)
```

- [ ] **Step 7: Add test for disabled_analyzers in test_config.py**

Find `tests/test_config.py` and add:

```python
def test_load_config_reads_disabled_analyzers(tmp_path: Path) -> None:
    toml = tmp_path / "code-review.toml"
    toml.write_text('disabled_analyzers = ["trivy", "pydeps"]\n')
    from code_review.config import load_config

    cfg = load_config(tmp_path)
    assert cfg.disabled_analyzers == ["trivy", "pydeps"]


def test_load_config_disabled_analyzers_default_empty(tmp_path: Path) -> None:
    from code_review.config import load_config

    cfg = load_config(tmp_path)  # no toml file
    assert cfg.disabled_analyzers == []
```

- [ ] **Step 8: Enforce disabled_analyzers in cli.py**

In `code_review/cli.py` `main()`, after loading config and before running analyzers, add:

```python
disabled = set(config.disabled_analyzers)
explicitly_disabled = [n for n in analyzer if n in disabled]
if explicitly_disabled:
    typer.echo(
        f"Error: analyzer(s) disabled in code-review.toml: {', '.join(explicitly_disabled)}",
        err=True,
    )
    raise typer.Exit(1)
```

- [ ] **Step 9: Write sandbox compatibility test**

Note: gitleaks, trivy, and semgrep all use `tempfile.TemporaryDirectory` for scratch files
(not CWD-relative paths). The sandbox test verifies that no stray files appear in CWD
and that the adapters return valid output despite writing to $TMPDIR.

```python
# tests/test_sandbox_compatibility.py
"""
Verify adapters do not litter the working directory with temp files.
All binary adapters (gitleaks, trivy, semgrep) use tempfile.TemporaryDirectory
so their scratch files land in $TMPDIR and are auto-cleaned — never in CWD.
"""
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
import json


async def test_gitleaks_no_temp_files_in_cwd(tmp_path):
    """GitleaksAdapter must not create any files in CWD."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        for arg in args:
            s = str(arg)
            if s.endswith(".sarif"):
                Path(s).write_text('{"version":"2.1.0","$schema":"x","runs":[]}')
                break
        return SubprocessResult(b"", b"", 0)

    before = set(tmp_path.iterdir())
    with (
        patch("code_review.adapters.gitleaks.run_subprocess", side_effect=fake_run),
        patch("os.getcwd", return_value=str(tmp_path)),
    ):
        request = ReviewRequest(scope="per-task", diff_range=None,
                                target_paths=(".",), languages=frozenset(), config={})
        output = await GitleaksAdapter().run(request)

    after = set(tmp_path.iterdir())
    assert before == after, f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"


async def test_trivy_no_temp_files_in_cwd(tmp_path):
    """TrivyAdapter must not create any files in CWD."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    cache_dir = tmp_path / "trivy-db"
    cache_dir.mkdir()

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        for i, arg in enumerate(args):
            if str(arg) == "--output" and i + 1 < len(args):
                Path(str(args[i + 1])).write_text(
                    '{"version":"2.1.0","$schema":"x","runs":[]}'
                )
                break
        return SubprocessResult(b"", b"", 0)

    before = set(tmp_path.iterdir())
    with (
        patch("code_review.adapters.trivy._TRIVY_CACHE_DIR", cache_dir),
        patch("code_review.adapters.trivy.run_subprocess", side_effect=fake_run),
        patch("os.getcwd", return_value=str(tmp_path)),
    ):
        request = ReviewRequest(scope="per-task", diff_range=None,
                                target_paths=(str(tmp_path),),
                                languages=frozenset(), config={})
        output = await TrivyAdapter().run(request)

    after = set(tmp_path.iterdir() )
    assert {p for p in after if p != cache_dir} == {p for p in before if p != cache_dir}, \
        f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"
```

- [ ] **Step 10: Run all new tests**

```bash
uv run pytest tests/test_lang_select.py tests/test_sandbox_compatibility.py \
    tests/test_config.py -v
```
Expected: all pass

- [ ] **Step 11: Full suite + lint + mypy**

```bash
uv run pytest --tb=short -q
uv run ruff check .
uv run mypy --config-file pyproject.toml code_review/
```
Expected: green except the semgrep integration test (now fixed in t7). Check total count.

- [ ] **Step 12: Commit**

```bash
git add code_review/adapters/__init__.py code_review/capabilities.json \
    code_review/lang_select.py code_review/config.py code_review/cli.py \
    tests/test_lang_select.py tests/test_sandbox_compatibility.py tests/test_config.py
git commit -m "code-review s3-t11: REGISTRY wiring, lang_select, disabled_analyzers, cross-cutting tests"
```

---

## Self-review checklist

- [ ] **Spec coverage**
  - All 10 adapters (bandit ✓, vulture ✓, pydeps ✓, cohesion ✓, gitleaks ✓, trivy ✓, eslint ✓, jscpd ✓, knip ✓, depcruiser ✓) → task
  - Analyzer Protocol conformance → every adapter test has `test_*_protocol_conformance`
  - SARIF-native adapters pass through → gitleaks, trivy, eslint (with formatter)
  - Non-SARIF adapters emit shim → bandit, vulture, pydeps, cohesion, jscpd, knip, depcruiser
  - Metrics-producing adapters → pydeps (coupling), cohesion (per_class)
  - JS vendored binaries → t8-t10 use `node_binary()` from js_base
  - Trivy offline → t6 uses `--skip-db-update --offline-scan`, cache-absent error
  - Semgrep offline → t7 uses local rules + `SEMGREP_USER_DATA_FOLDER`
  - No writes outside CWD → t11 sandbox test; gitleaks/trivy/semgrep all use tempfile.TemporaryDirectory
  - disabled_analyzers → t11 Config field + cli enforcement
  - Per-language selection → t11 lang_select.py
  - Timeout handling → `run_subprocess` already handles this in base.py; each adapter returns `status="timeout"` on `result.timed_out`
  - Setup-not-run (unavailable) → trivy checks cache dir; js adapters check `node_binary()`
  - capabilities.json updated → t11

- [ ] **Placeholder scan:** No TBD/TODO/placeholder text present ✓

- [ ] **Type consistency:**
  - `empty_sarif` used in: bandit, vulture, pydeps, cohesion, gitleaks, eslint, jscpd, knip, depcruiser — all pass `tool_name: str` ✓
  - `node_tool: ClassVar[str]` used in: eslint, jscpd, knip, depcruiser — all match the `_probe_analyzer` check in cli.py ✓
  - `required_binary: ClassVar[str]` used in: gitleaks, trivy, semgrep — all match the `_probe_analyzer` check ✓
  - `MetricSet` returned by: pydeps (coupling), cohesion (per_class) — both match `contracts.py` field names ✓
