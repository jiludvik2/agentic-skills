#!/usr/bin/env python3
"""analyzer-coverage smoke test.

Runs every analyzer in the polyreview registry against a synthetic fixture that
plants exactly the defect the analyzer should surface, then asserts the analyzer
(a) ran (bundle status ``ok``) and (b) produced the expected signal in its **raw
native output**. As of the thin-runner re-architecture (ADR-0020) the CLI emits a
``review-bundle.v1.json`` — one raw ``CaptureOutput`` per tool — so this harness
reads that bundle and routes each tool's raw stdout through ``bundle_oracle`` (no
consolidated SARIF/metrics schema any more). Writes a Markdown results report and
the raw per-analyzer bundle JSON.

Run from the repo root (code-review/), under the project venv:

    uv run python sdlc/docs/qa/analyzer-coverage/run_smoke.py

Prerequisites (see README.md): scripts/setup.sh has run (Node tooling vendored),
the Trivy DB is pre-fetched, gitleaks+trivy are on PATH, and the vendored semgrep
ruleset is provisioned. (schemathesis was removed from the registry by ADR-0021,
so the harness no longer stands up a FastAPI server.)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # .../code-review
SKILL = REPO / ".claude" / "skills" / "code-review"
FIX = HERE / "fixtures"
RESULTS = HERE / "results"
RAW = RESULTS / "raw"

# bundle_oracle is a sibling module in this QA dir (outside the code_review package).
sys.path.insert(0, str(HERE))
import bundle_oracle as bo  # noqa: E402


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = "/opt/homebrew/bin:" + env.get("PATH", "")
    env["POLYREVIEW_CACHE_DIR"] = str(SKILL)
    # NODE_PATH is no longer set here: the eslint adapter exports it to the
    # vendored node_modules itself (s1-t2) so the SARIF formatter resolves
    # regardless of cwd. POLYREVIEW_CACHE_DIR anchors node_modules_dir().
    return env


def _run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    # The CLI exposes analyzer execution under the `run` subcommand (the two-step
    # plan/run flow introduced with the bundle migration, s1-t3); the selectors
    # (--analyzer/--target/--output) live under it.
    proc = subprocess.run(
        [sys.executable, "-m", "code_review.cli", "run", *args],
        cwd=str(cwd),
        env=_env(),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# Each check takes a tool's raw native stdout (str) and returns (ok, detail).
def _count_check(counter, minimum: int = 1):
    def check(stdout: str) -> tuple[bool, str]:
        n = counter(stdout)
        return n >= minimum, f"{n} finding(s)"
    return check


def _radon_check(stdout: str) -> tuple[bool, str]:
    cc = bo.max_cc(stdout)
    return cc >= 10, f"max_cc={cc}"


def _pydeps_fanout_check(stdout: str) -> tuple[bool, str]:
    # Loose: the coupling graph was computed (the high-fan-out fixture). pydeps under-counts
    # re-exported leaf imports, so we assert the graph exists rather than a fan-out threshold.
    fo = bo.pydeps_max_fanout(stdout)
    return fo >= 1, f"max_fan_out={fo}"


def _pydeps_cycle_check(stdout: str) -> tuple[bool, str]:
    ok = bo.pydeps_has_cycle(stdout, "cyclepkg.a", "cyclepkg.b")
    return ok, "a↔b back-edge present" if ok else "cycle NOT detected"


def _depcruiser_circular_check(stdout: str) -> tuple[bool, str]:
    ok = bo.depcruiser_has_circular(stdout)
    return ok, "circular edge present" if ok else "no circular edge"


def _depcruiser_mocks_check(stdout: str) -> tuple[bool, str]:
    ok = bo.depcruiser_has_edge_into(stdout, "__mocks__")
    return ok, "prod→__mocks__ edge present" if ok else "no prod→__mocks__ edge"


PY = FIX / "python"
JS = FIX / "js"

# Labels whose failure is a known, documented, out-of-scope defect — reported as XFAIL
# (visible, not hidden) and excluded from the exit code so the harness still goes green on
# the documented-good state. See FINDINGS.md for each entry's rationale + follow-up.
KNOWN_DEFERRED = {
    # gitleaks adapter invokes `gitleaks detect` with no `--report-format json`, so findings
    # go to stderr (human format) and captured stdout is empty → oracle counts 0. Fixing it
    # is a shipping-adapter change (off-argv JSON report path), tracked as a follow-up.
    "gitleaks": "adapter emits no JSON on stdout — see FINDINGS.md (output-capture follow-up)",
}

# (label, analyzer, cwd, target (passed to --target), check, note)
# label names the harness row + raw file; analyzer is the --analyzer id invoked.
CASES = [
    ("bandit", "bandit", REPO, str(PY),
     _count_check(bo.count_bandit), "shell=True, md5, eval, pickle"),
    ("semgrep", "semgrep", REPO, str(PY),
     _count_check(bo.count_sarif_results), "eval + shell=True (local rules)"),
    ("gitleaks", "gitleaks", REPO, str(PY),
     _count_check(bo.count_gitleaks), "hardcoded AWS/GitHub/Slack creds"),
    # trivy is invoked with `--format sarif`, so the bundle stdout is SARIF, not
    # trivy's native {"Results": …} JSON — count SARIF results.
    ("trivy", "trivy", REPO, str(FIX / "deps"),
     _count_check(bo.count_sarif_results), "PyYAML 5.1 / requests 2.19.0 CVEs"),
    ("radon", "radon", REPO, str(PY),
     _radon_check, "cyclomatic complexity (metrics-only)"),
    ("vulture", "vulture", REPO, str(PY),
     _count_check(bo.count_text_lines), "unused import/func/class/var"),
    ("cohesion", "cohesion", REPO, str(PY),
     _count_check(bo.count_text_lines), "GrabBag low-cohesion class"),
    ("pydeps", "pydeps", PY, "couplingpkg",
     _pydeps_fanout_check, "hub.py coupling graph"),
    ("pydeps-cycles", "pydeps", PY, "cyclepkg",
     _pydeps_cycle_check, "labelled a→b→a import cycle"),
    ("eslint", "eslint", JS, ".",
     _count_check(bo.count_sarif_results), "lint_me.js: no-unused-vars + no-debugger"),
    ("knip", "knip", REPO, str(JS),
     _count_check(bo.count_knip), "unused files (entry=src/index.ts)"),
    ("jscpd", "jscpd", REPO, str(JS / "src"),
     _count_check(bo.count_jscpd), "clone_a/clone_b duplication"),
    ("depcruiser", "depcruiser", JS, "src",
     _depcruiser_circular_check, "cycle_a <-> cycle_b circular"),
    ("depcruiser-mocks", "depcruiser", JS, "src",
     _depcruiser_mocks_check, "src/app.ts → __mocks__/service.ts"),
]


def _require_provisioned_semgrep_rules() -> None:
    """Assert the vendored semgrep ruleset is already in the runtime cache — i.e.
    setup.sh has run. The harness no longer self-provisions (s0-t3 / ADR-0016):
    its job is to prove a clean `setup.sh` is sufficient, so it fails loud here
    rather than silently copying rules in (which is what hid F3)."""
    rules = SKILL / "cache" / "semgrep" / "rules"
    if not rules.is_dir() or not list(rules.glob("*.y*ml")):
        sys.exit(
            f"semgrep rules not provisioned at {rules}. Run scripts/setup.sh "
            "(or scripts/prefetch_caches.py) before the smoke test."
        )


def run_standard() -> list[dict]:
    rows = []
    for label, analyzer, cwd, target, check, note in CASES:
        rel_out = f".qa_{label}.json"  # written within cwd to satisfy the --output guard
        tmp_out = cwd / rel_out
        rc, stdout, stderr = _run_cli(
            ["--analyzer", analyzer, "--target", target, "--output", rel_out],
            cwd=cwd,
        )
        final = RAW / f"{label}.json"
        if tmp_out.exists():
            tmp_out.replace(final)
        rows.append(_evaluate(label, analyzer, final, rc, stderr, check, note))
    return rows


def _evaluate(label, analyzer, out_path, rc, stderr, check, note) -> dict:
    if not out_path.exists():
        return {"label": label, "analyzer": analyzer, "status": "error", "ok": False,
                "detail": f"no output (rc={rc}): {stderr.strip()[:200]}", "note": note}
    try:
        bundle = json.loads(out_path.read_text())
    except ValueError as exc:
        return {"label": label, "analyzer": analyzer, "status": "error", "ok": False,
                "detail": f"bundle not JSON: {exc}", "note": note}
    status = bo.status_of(bundle, analyzer)
    if status != "ok":
        out = bo.output_for(bundle, analyzer) or {}
        detail = (out.get("error") or out.get("stderr") or "")[:200]
        return {"label": label, "analyzer": analyzer, "status": status, "ok": False,
                "detail": f"status={status}: {detail}".rstrip(": "), "note": note}
    out = bo.output_for(bundle, analyzer) or {}
    ok, detail = check(out.get("stdout", ""))
    return {"label": label, "analyzer": analyzer, "status": status, "ok": ok,
            "detail": detail, "note": note}


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    _require_provisioned_semgrep_rules()
    rows = run_standard()

    passed = sum(1 for r in rows if r["ok"])
    total = len(rows)
    # A non-deferred failure is a real regression; known-deferred ones (KNOWN_DEFERRED)
    # are reported as XFAIL and don't fail the run.
    real_failures = [
        r for r in rows if not r["ok"] and r["label"] not in KNOWN_DEFERRED
    ]

    # ---- write Markdown report ----
    lines = [
        f"# Analyzer-coverage smoke results — {date.today().isoformat()}",
        "",
        f"**{passed}/{total} analyzer cases produced their expected signal.** "
        "Generated by `run_smoke.py`. Raw per-analyzer review bundle in `raw/`.",
        "",
        "| Case | Result | Bundle status | Observed | Planted defect |",
        "|------|--------|---------------|----------|----------------|",
    ]
    for r in sorted(rows, key=lambda x: x["label"]):
        if r["ok"]:
            mark = "✅ pass"
        elif r["label"] in KNOWN_DEFERRED:
            mark = "⚠️ xfail"
        else:
            mark = "❌ FAIL"
        lines.append(
            f"| `{r['label']}` | {mark} | {r['status']} | {r['detail']} | {r['note']} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Each case reads the tool's **raw native** stdout from the review bundle "
        "(ADR-0020) via `bundle_oracle` — no consolidated SARIF/metrics layer.",
        "- **radon** asserts `max_cc >= 10` from `radon cc --json`; **pydeps** "
        "(`couplingpkg`) asserts the coupling graph was computed.",
        "- **pydeps-cycles** and **depcruiser-mocks** are *precision* oracles: they "
        "assert the *specific* planted coupling defect (the a↔b import back-edge / the "
        "prod→`__mocks__` edge), so a tool that runs but stops detecting fails loudly.",
        "- **semgrep** runs against the vendored ruleset that `setup.sh` provisions "
        "into `cache/semgrep/rules` (ADR-0016); offline and deterministic.",
        "- **xfail** rows are known, documented, out-of-scope defects (see "
        "`KNOWN_DEFERRED` in `run_smoke.py` + FINDINGS.md); they are reported but do "
        "not fail the run.",
        "- Fixtures live in `fixtures/` and are regenerable via `scaffold_fixtures.sh`.",
        "",
    ]
    report = RESULTS / f"{date.today().isoformat()}-results.md"
    report.write_text("\n".join(lines))

    # ---- console summary ----
    deferred = total - passed - len(real_failures)
    print(f"\n=== {passed}/{total} analyzer cases passed "
          f"({deferred} xfail, {len(real_failures)} real failure(s)) ===")
    for r in sorted(rows, key=lambda x: x["label"]):
        if r["ok"]:
            mark = "PASS"
        elif r["label"] in KNOWN_DEFERRED:
            mark = "XFAIL"
        else:
            mark = "FAIL"
        print(f"  [{mark}] {r['label']:<17} {r['status']:<8} {r['detail']}")
    print(f"\nReport: {report}")
    # Green when there are no *real* (non-deferred) failures.
    return 0 if not real_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
