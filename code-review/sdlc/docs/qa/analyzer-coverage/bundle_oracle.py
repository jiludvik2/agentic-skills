"""Bundle oracle for the analyzer-coverage QA harness (s5 / G5).

Pure, dependency-free readers over a ``review-bundle.v1.json`` document (ADR-0020). The
bundle carries each tool's **raw native** stdout — *not* a normalized schema — so each
extractor here parses the tool's own output format and answers "did the planted defect
appear?". Two of them are **precision oracles** that assert a *specific* labelled coupling
defect (pydeps import cycle, depcruiser prod→``__mocks__`` edge), so a tool that runs but
silently stops detecting is caught.

This module lives in the QA dir (outside the ``code_review`` package) and is consumed both
by ``run_smoke.py`` (the harness orchestrator) and by ``tests/test_qa_bundle_oracle.py``
(unit tests over hand-authored snippets, no binaries). Stdlib only.

Every extractor is defensive: malformed/empty stdout yields a zero/``False`` signal rather
than raising — a crashing oracle would mask a real tool result. Some native shapes
(knip/jscpd/schemathesis) are authored to their documented form and reconciled against real
captured output in s5-t2.
"""

from __future__ import annotations

import json
from typing import Any


def _loads(stdout: str) -> Any:
    try:
        return json.loads(stdout)
    except (ValueError, TypeError):
        return None


def _segments(path: str) -> list[str]:
    return path.replace("\\", "/").split("/")


def _path_has_segment(path: str, needle: str) -> bool:
    """True iff ``needle`` appears as a full path segment of ``path`` (e.g. ``__mocks__``
    in ``src/__mocks__/x.js``), avoiding substring false positives."""
    return needle in _segments(path)


# --------------------------------------------------------------------------- #
# Bundle accessors
# --------------------------------------------------------------------------- #


def output_for(bundle: dict[str, Any], tool: str) -> dict[str, Any] | None:
    """The ``outputs[]`` entry whose ``tool == tool``, or ``None``."""
    for out in bundle.get("outputs", []) or []:
        if isinstance(out, dict) and out.get("tool") == tool:
            return out
    return None


def status_of(bundle: dict[str, Any], tool: str) -> str:
    """The tool's ADR-0019 status (``ok``/``error``/``timeout``/``unavailable``), or
    ``"missing"`` if the tool is absent from the bundle."""
    out = output_for(bundle, tool)
    if out is None:
        return "missing"
    status = out.get("status", "missing")
    return status if isinstance(status, str) else "missing"


# --------------------------------------------------------------------------- #
# SARIF emitters (semgrep / eslint / jscomplexity)
# --------------------------------------------------------------------------- #


def count_sarif_results(stdout: str) -> int:
    data = _loads(stdout)
    if not isinstance(data, dict):
        return 0
    total = 0
    for run in data.get("runs", []) or []:
        if isinstance(run, dict):
            total += len(run.get("results", []) or [])
    return total


# --------------------------------------------------------------------------- #
# Native finding counters
# --------------------------------------------------------------------------- #


def count_bandit(stdout: str) -> int:
    data = _loads(stdout)
    if not isinstance(data, dict):
        return 0
    return len(data.get("results", []) or [])


def count_gitleaks(stdout: str) -> int:
    """gitleaks ``--report-format json`` emits a top-level JSON array of findings."""
    data = _loads(stdout)
    return len(data) if isinstance(data, list) else 0


def count_trivy(stdout: str) -> int:
    data = _loads(stdout)
    if not isinstance(data, dict):
        return 0
    total = 0
    for result in data.get("Results", []) or []:
        if isinstance(result, dict):
            total += len(result.get("Vulnerabilities") or [])
    return total


def count_knip(stdout: str) -> int:
    """knip ``--reporter json``: ``{"files": [...], "issues": [...]}``. Count unused files
    plus issues. (Exact issues shape varies by knip version — reconciled in s5-t2.)"""
    data = _loads(stdout)
    if not isinstance(data, dict):
        return 0
    files = data.get("files", []) or []
    issues = data.get("issues", []) or []
    n_files = len(files) if isinstance(files, (list, dict)) else 0
    n_issues = len(issues) if isinstance(issues, (list, dict)) else 0
    return n_files + n_issues


def count_jscpd(stdout: str) -> int:
    data = _loads(stdout)
    if not isinstance(data, dict):
        return 0
    return len(data.get("duplicates", []) or [])


def count_schemathesis(stdout: str) -> int:
    """Loose failure count from schemathesis JSON (documented shape ``{"failures": [...]}``;
    reconciled against real captured output in s5-t2)."""
    data = _loads(stdout)
    if not isinstance(data, dict):
        return 0
    return len(data.get("failures", []) or [])


# --------------------------------------------------------------------------- #
# radon (cyclomatic complexity, metrics-only)
# --------------------------------------------------------------------------- #


def max_cc(stdout: str) -> int:
    """Max ``complexity`` across all functions in ``radon cc --json`` output
    (``{path: [{complexity: N, ...}, ...]}``)."""
    data = _loads(stdout)
    if not isinstance(data, dict):
        return 0
    best = 0
    for entries in data.values():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    cc = entry.get("complexity", 0)
                    if isinstance(cc, (int, float)) and cc > best:
                        best = int(cc)
    return best


# --------------------------------------------------------------------------- #
# Text emitters (vulture / cohesion)
# --------------------------------------------------------------------------- #


def count_text_lines(stdout: str) -> int:
    """Count non-blank report lines (vulture/cohesion emit one finding per line)."""
    return sum(1 for line in stdout.splitlines() if line.strip())


# --------------------------------------------------------------------------- #
# pydeps — import-cycle precision oracle
# --------------------------------------------------------------------------- #


def _pydeps_imports(graph: dict[str, Any], module: str) -> list[str]:
    node = graph.get(module)
    if isinstance(node, dict):
        imports = node.get("imports", []) or []
        if isinstance(imports, list):
            return imports
    return []


def pydeps_has_cycle(stdout: str, a: str, b: str) -> bool:
    """True iff pydeps' dependency graph contains the mutual back-edge ``a ↔ b`` — i.e.
    ``a`` imports ``b`` **and** ``b`` imports ``a``. The graph is pydeps' ``--show-deps``
    JSON: ``{module: {"imports": [...], "imported_by": [...]}}`` with dotted module names."""
    graph = _loads(stdout)
    if not isinstance(graph, dict):
        return False
    return b in _pydeps_imports(graph, a) and a in _pydeps_imports(graph, b)


def pydeps_max_fanout(stdout: str) -> int:
    """Max fan-out (number of ``imports``) across all modules in pydeps' graph — the loose
    "coupling graph was computed" signal for the high-fan-out fixture (not a precision
    oracle; the cycle fixture has the precision oracle above)."""
    graph = _loads(stdout)
    if not isinstance(graph, dict):
        return 0
    return max((len(_pydeps_imports(graph, m)) for m in graph), default=0)


# --------------------------------------------------------------------------- #
# depcruiser — coupling precision oracles
# --------------------------------------------------------------------------- #


def depcruiser_has_edge_into(
    stdout: str, needle: str, from_outside: bool = True
) -> bool:
    """True iff depcruiser's module graph has a dependency edge whose *resolved* path has a
    ``needle`` segment (e.g. ``__mocks__``). With ``from_outside`` (default), the edge's
    *source* must lie outside ``needle`` — i.e. production code depending on a mock (the
    prod→``__mocks__`` coupling smell), not an intra-mock edge.

    depcruiser ``--output-type json`` shape:
    ``{"modules": [{"source": str, "dependencies": [{"resolved": str, "circular": bool}]}]}``.
    """
    data = _loads(stdout)
    if not isinstance(data, dict):
        return False
    for module in data.get("modules", []) or []:
        if not isinstance(module, dict):
            continue
        source = module.get("source", "") or ""
        if from_outside and _path_has_segment(source, needle):
            continue
        for dep in module.get("dependencies", []) or []:
            if isinstance(dep, dict) and _path_has_segment(dep.get("resolved", "") or "", needle):
                return True
    return False


def depcruiser_has_circular(stdout: str) -> bool:
    """True iff any dependency in depcruiser's graph is flagged ``circular: true`` (the
    existing ``cycle_a/cycle_b`` case, migrated to raw output)."""
    data = _loads(stdout)
    if not isinstance(data, dict):
        return False
    for module in data.get("modules", []) or []:
        if isinstance(module, dict):
            for dep in module.get("dependencies", []) or []:
                if isinstance(dep, dict) and dep.get("circular") is True:
                    return True
    return False
