"""s2-t1 — output-capture coverage guard.

The gitleaks false-negative (s2-t0) shipped because the adapter emitted findings to
stderr while the bundle's contract (ADR-0020) promises them in ``outputs[].stdout`` —
and the analyzer-coverage harness allow-listed the resulting zero-signal as an xfail.

This guard makes that class of silent false-negative hard to reintroduce: every
deterministic adapter in the registry MUST have a positive-signal case in the QA
``run_smoke.py`` harness, whose oracles parse ``stdout`` exclusively. A new or changed
adapter that emits findings anywhere but stdout would then count zero against its case
and turn the harness red (it is no longer allow-listed). An adapter added without a
case fails this test outright.

See ``sdlc/docs/qa/analyzer-coverage/output-capture-audit.md`` for the per-adapter
channel audit this guard backs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_QA_DIR = Path(__file__).parent.parent / "sdlc" / "docs" / "qa" / "analyzer-coverage"


def _load_run_smoke() -> ModuleType:
    """Load the QA harness module by path (it lives outside the package, alongside its
    ``bundle_oracle`` sibling — which it imports via ``sys.path``). Restores ``sys.path``
    so the QA dir does not leak onto it for the rest of the session (run_smoke.py inserts
    its own dir too; we undo ours)."""
    saved = list(sys.path)
    try:
        sys.path.insert(0, str(_QA_DIR))
        spec = importlib.util.spec_from_file_location("qa_run_smoke", _QA_DIR / "run_smoke.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path[:] = saved


def test_every_deterministic_adapter_has_positive_signal_case() -> None:
    from code_review.adapters import REGISTRY

    rs = _load_run_smoke()
    # CASES rows are (label, analyzer_id, cwd, target, check, note). Duplicate analyzer_ids
    # (pydeps/depcruiser each have two precision rows) collapse in the set.
    case_analyzer_ids = {row[1] for row in rs.CASES}
    # Scope to deterministic adapters explicitly: the guard's contract is about tools whose
    # findings the harness counts from stdout. A future `contract`-kind adapter (the role
    # schemathesis held) would not belong in this set and must not force a bogus CASE.
    deterministic = {k for k, v in REGISTRY.items() if getattr(v, "kind", None) == "deterministic"}
    missing = deterministic - case_analyzer_ids
    assert not missing, (
        f"deterministic adapters with no positive-signal case in run_smoke.py: "
        f"{sorted(missing)} — every adapter must have a ≥1-signal-in-stdout case so a "
        "silent (stderr-only / unread-file) adapter cannot pass green (the gitleaks "
        "s2-t0 false-negative class). Add a CASE row, or a documented exclusion."
    )


def test_known_deferred_carries_no_stdout_capture_xfail() -> None:
    """A stdout-capture defect must never be parked as an xfail again (that is exactly
    how the gitleaks false-negative hid). Any future xfail must be for a different,
    explicitly-stated reason. This is a lexical proxy (it matches the reason text, not the
    semantics) — adequate because KNOWN_DEFERRED entries are rare and human-reviewed."""
    rs = _load_run_smoke()
    offenders = {
        label: reason
        for label, reason in rs.KNOWN_DEFERRED.items()
        if "stdout" in reason.lower() or "output-capture" in reason.lower()
    }
    assert not offenders, (
        f"xfail entries that re-park a stdout-capture false-negative: {offenders}. "
        "Fix the adapter (off-argv report read-back, the s2-t0 pattern) instead."
    )
