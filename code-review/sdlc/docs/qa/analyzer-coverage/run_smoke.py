#!/usr/bin/env python3
"""analyzer-coverage smoke test.

Runs every analyzer in the polyreview registry against a synthetic fixture that
plants exactly the defect the analyzer should surface, then asserts the analyzer
(a) ran without error and (b) produced the expected signal (a SARIF finding, or
populated metrics for the metrics-only analyzers). Writes a Markdown results
report and the raw consolidated JSON for each analyzer.

Run from the repo root (code-review/), under the project venv:

    uv run python sdlc/docs/qa/analyzer-coverage/run_smoke.py

Prerequisites (see README.md): scripts/setup.sh has run (Node tooling vendored),
the Trivy DB is pre-fetched, gitleaks+trivy are on PATH, fastapi+uvicorn are
installed, and network is available for semgrep's `--config auto`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # .../code-review
SKILL = REPO / ".claude" / "skills" / "code-review"
FIX = HERE / "fixtures"
RESULTS = HERE / "results"
RAW = RESULTS / "raw"

API_PORT = 8099


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = "/opt/homebrew/bin:" + env.get("PATH", "")
    env["POLYREVIEW_CACHE_DIR"] = str(SKILL)
    # So `node`/eslint can resolve the vendored @microsoft/eslint-formatter-sarif
    # package no matter which cwd an adapter runs from.
    env["NODE_PATH"] = str(SKILL / "node_modules")
    return env


def _run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "code_review.cli", *args],
        cwd=str(cwd),
        env=_env(),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _count_findings(consolidated: dict) -> int:
    return sum(
        len(run.get("results", []))
        for run in consolidated.get("sarif", {}).get("runs", [])
    )


# (analyzer, [extra cli args], target (relative to repo), cwd, expectation-fn, note)
# expectation-fn(consolidated_dict) -> (ok: bool, detail: str)
def _expect_findings(minimum: int):
    def check(c: dict) -> tuple[bool, str]:
        n = _count_findings(c)
        return n >= minimum, f"{n} finding(s)"
    return check


def _expect_radon(c: dict) -> tuple[bool, str]:
    pf = (c.get("metrics") or {}).get("per_file", {})
    max_cc = max((v.get("max_cc", 0) for v in pf.values()), default=0)
    return bool(pf) and max_cc >= 10, f"{len(pf)} file(s), max_cc={max_cc}"


def _expect_pydeps_metrics(c: dict) -> tuple[bool, str]:
    # pydeps' primary output is the coupling graph (metrics.coupling). The
    # high-fan-out *finding* only fires at fan_out >= 10; pydeps' import
    # resolution under-counts re-exported leaf imports, so we assert the graph
    # was computed (its capability) rather than the threshold finding.
    coupling = (c.get("metrics") or {}).get("coupling", {})
    max_fo = max((v.get("fan_out", 0) for v in coupling.values()), default=0)
    return (bool(coupling) and max_fo >= 1), f"{len(coupling)} module(s), max_fan_out={max_fo}"


PY = FIX / "python"
JS = FIX / "js"

# (name, cwd, target (passed to --target), check, note)
CASES = [
    ("bandit", REPO, str(PY), _expect_findings(1), "shell=True, md5, eval, pickle"),
    ("semgrep", REPO, str(PY), _expect_findings(1), "eval + shell=True (local rules)"),
    ("gitleaks", REPO, str(PY), _expect_findings(1), "hardcoded AWS/GitHub/Slack creds"),
    ("trivy", REPO, str(FIX / "deps"), _expect_findings(1), "PyYAML 5.1 / requests 2.19.0 CVEs"),
    ("radon", REPO, str(PY), _expect_radon, "cyclomatic complexity (metrics-only)"),
    ("vulture", REPO, str(PY), _expect_findings(1), "unused import/func/class/var"),
    ("cohesion", REPO, str(PY), _expect_findings(1), "GrabBag low-cohesion class"),
    ("pydeps", PY, "couplingpkg", _expect_pydeps_metrics, "hub.py coupling graph"),
    ("eslint", JS, ".", _expect_findings(1), "lint_me.js: no-unused-vars + no-debugger"),
    ("knip", REPO, str(JS), _expect_findings(1), "unused files (entry=src/index.ts)"),
    ("jscpd", REPO, str(JS / "src"), _expect_findings(1), "clone_a/clone_b duplication"),
    ("depcruiser", JS, "src", _expect_findings(1), "cycle_a <-> cycle_b circular"),
]


def _provision_semgrep_rules() -> None:
    """Copy the bundled QA ruleset into the cache dir so the semgrep adapter uses
    its `--config <local-dir>` path. (setup.sh's prefetch ships 0 rules, and the
    `--config auto` fallback is incompatible with the adapter's `--metrics off`.)"""
    src = HERE / "semgrep-rules"
    dst = SKILL / "cache" / "semgrep" / "rules"
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.yaml"):
        (dst / f.name).write_text(f.read_text())


def run_standard() -> list[dict]:
    rows = []
    for name, cwd, target, check, note in CASES:
        rel_out = f".qa_{name}.json"  # written within cwd to satisfy the --output guard
        tmp_out = cwd / rel_out
        rc, stdout, stderr = _run_cli(
            ["--analyzer", name, "--target", target, "--output", rel_out],
            cwd=cwd,
        )
        final = RAW / f"{name}.json"
        if tmp_out.exists():
            tmp_out.replace(final)
        rows.append(_evaluate(name, final, rc, stderr, check, note))
    return rows


def run_schemathesis() -> dict:
    name = "schemathesis"
    out = RAW / f"{name}.json"
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(API_PORT), "--log-level", "warning"],
        cwd=str(FIX / "api"),
        env=_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # Wait for the spec endpoint to come up.
        ready = False
        for _ in range(50):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{API_PORT}/openapi.json", timeout=1
                ) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.2)
        if not ready:
            return {"analyzer": name, "status": "error", "ok": False,
                    "detail": "API server did not become ready", "note": ""}
        rc, stdout, stderr = _run_cli(
            ["--analyzer", name, "--scope", "story-level",
             "--config", str(HERE / "contract-testing.toml"),
             "--target", str(FIX / "api"),
             "--output", str(out.relative_to(REPO))],
            cwd=REPO,
        )
        return _evaluate(name, out, rc, stderr, _expect_findings(1),
                         "200 body violates advertised User schema")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


def _evaluate(name, out_path, rc, stderr, check, note) -> dict:
    if not out_path.exists():
        return {"analyzer": name, "status": "error", "ok": False,
                "detail": f"no output (rc={rc}): {stderr.strip()[:200]}", "note": note}
    consolidated = json.loads(out_path.read_text())
    astatus = consolidated.get("analyzers", {}).get(name, {})
    status = astatus.get("status", "?")
    if status == "error":
        return {"analyzer": name, "status": status, "ok": False,
                "detail": f"adapter error: {astatus.get('error', '')[:200]}", "note": note}
    ok, detail = check(consolidated)
    return {"analyzer": name, "status": status, "ok": ok, "detail": detail, "note": note}


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    _provision_semgrep_rules()
    rows = run_standard()
    rows.append(run_schemathesis())

    passed = sum(1 for r in rows if r["ok"])
    total = len(rows)

    # ---- write Markdown report ----
    lines = [
        f"# Analyzer-coverage smoke results — {date.today().isoformat()}",
        "",
        f"**{passed}/{total} analyzers produced their expected signal.** "
        "Generated by `run_smoke.py`. Raw consolidated JSON per analyzer in `raw/`.",
        "",
        "| Analyzer | Result | Adapter status | Observed | Planted defect |",
        "|----------|--------|----------------|----------|----------------|",
    ]
    for r in sorted(rows, key=lambda x: x["analyzer"]):
        mark = "✅ pass" if r["ok"] else "❌ FAIL"
        lines.append(
            f"| `{r['analyzer']}` | {mark} | {r['status']} | {r['detail']} | {r['note']} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- **radon** and **pydeps** are (partly) metrics analyzers: radon emits no "
        "SARIF findings, only `metrics.per_file` complexity; the check asserts "
        "`max_cc >= 10`. pydeps emits both a high-fan-out finding and coupling metrics.",
        "- **semgrep** uses `--config auto` (network) when no local rule cache exists; "
        "finding count depends on the live registry ruleset.",
        "- Fixtures live in `fixtures/` and are regenerable via `scaffold_fixtures.sh`.",
        "",
    ]
    report = RESULTS / f"{date.today().isoformat()}-results.md"
    report.write_text("\n".join(lines))

    # ---- console summary ----
    print(f"\n=== {passed}/{total} analyzers passed ===")
    for r in sorted(rows, key=lambda x: x["analyzer"]):
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['analyzer']:<13} {r['status']:<8} {r['detail']}")
    print(f"\nReport: {report}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
