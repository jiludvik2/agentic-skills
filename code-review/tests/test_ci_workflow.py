"""s2-t4: structural assertions on .github/workflows/ci.yml — the push/PR
gating workflow that runs pytest + ruff + mypy on every change to code-review/."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW_PATH = (
    Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
)


def _on_block(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML's YAML 1.1 loader maps the bare key `on` to Python True. The
    # canonical GitHub Actions syntax is `on:`; both keys are accepted here.
    block = workflow.get("on") or workflow.get(True)
    assert isinstance(block, dict), f"`on` block must be a mapping; got {block!r}"
    return block


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    assert WORKFLOW_PATH.exists(), f"CI workflow missing at {WORKFLOW_PATH}"
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "ci.yml must parse as a mapping"
    return data


def test_ci_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists(), f"expected .github/workflows/ci.yml at {WORKFLOW_PATH}"


def test_triggers_are_push_main_and_pr_main(workflow: dict[str, Any]) -> None:
    on = _on_block(workflow)
    push = on.get("push", {})
    pr = on.get("pull_request", {})
    assert "main" in push.get("branches", []), (
        f"push.branches must include 'main'; got {push.get('branches')!r}"
    )
    assert "main" in pr.get("branches", []), (
        f"pull_request.branches must include 'main'; got {pr.get('branches')!r}"
    )


def test_path_filter_covers_code_review(workflow: dict[str, Any]) -> None:
    on = _on_block(workflow)
    for trigger_name in ("push", "pull_request"):
        paths = on.get(trigger_name, {}).get("paths", [])
        assert "code-review/**" in paths, (
            f"{trigger_name}.paths must include 'code-review/**'; got {paths!r}"
        )
        assert ".github/workflows/ci.yml" in paths, (
            f"{trigger_name}.paths must include '.github/workflows/ci.yml'; got {paths!r}"
        )


def test_single_test_job(workflow: dict[str, Any]) -> None:
    jobs = workflow.get("jobs", {})
    assert set(jobs.keys()) == {"test"}, (
        f"expected exactly one job named 'test'; got {sorted(jobs.keys())}"
    )


def test_no_elevated_permissions(workflow: dict[str, Any]) -> None:
    """CI is read-only — no OIDC, no write permissions on any contents."""
    workflow_perms = workflow.get("permissions", {})
    if isinstance(workflow_perms, dict):
        assert "id-token" not in workflow_perms, (
            "CI workflow must not declare id-token"
        )
        for key, value in workflow_perms.items():
            assert value in (None, "read", "none"), (
                f"CI workflow permission {key!r}={value!r} elevates beyond read-only"
            )

    for job_name, job in workflow.get("jobs", {}).items():
        perms = job.get("permissions", {})
        if isinstance(perms, dict):
            assert "id-token" not in perms, (
                f"job {job_name!r} must not declare id-token"
            )
            for key, value in perms.items():
                assert value in (None, "read", "none"), (
                    f"job {job_name!r} permission {key!r}={value!r} elevates beyond read-only"
                )


def test_steps_run_pytest_ruff_mypy_in_order(workflow: dict[str, Any]) -> None:
    """The green-bar trio must run in the documented order with the standard
    pytest marker filter."""
    steps = workflow["jobs"]["test"].get("steps", [])
    run_strings = [s.get("run", "") for s in steps if isinstance(s, dict) and "run" in s]

    indexed = list(enumerate(run_strings))
    sync_idx = next(
        (i for i, r in indexed if "uv sync --frozen" in r),
        None,
    )
    pytest_idx = next(
        (
            i for i, r in indexed
            if "uv run pytest" in r and "not slow" in r and "not integration" in r
        ),
        None,
    )
    ruff_idx = next(
        (i for i, r in indexed if "uv run ruff check" in r),
        None,
    )
    mypy_idx = next(
        (i for i, r in indexed if "uv run mypy" in r and "code_review" in r),
        None,
    )

    assert sync_idx is not None, (
        f"missing `uv sync --frozen` step; run strings: {run_strings}"
    )
    assert pytest_idx is not None, (
        f"missing pytest step with the not-slow/not-integration marker filter; "
        f"run strings: {run_strings}"
    )
    assert ruff_idx is not None, (
        f"missing `uv run ruff check` step; run strings: {run_strings}"
    )
    assert mypy_idx is not None, (
        f"missing `uv run mypy code_review` step; run strings: {run_strings}"
    )

    assert sync_idx < pytest_idx < ruff_idx < mypy_idx, (
        f"step order must be sync → pytest → ruff → mypy; "
        f"got indices sync={sync_idx} pytest={pytest_idx} ruff={ruff_idx} mypy={mypy_idx}"
    )


def test_setup_uv_v5_with_cache(workflow: dict[str, Any]) -> None:
    steps = workflow["jobs"]["test"].get("steps", [])
    setup_uv_steps = [
        s for s in steps
        if isinstance(s, dict)
        and str(s.get("uses", "")).startswith("astral-sh/setup-uv@")
    ]
    assert len(setup_uv_steps) == 1, (
        f"expected exactly one setup-uv step in test job; got {len(setup_uv_steps)}"
    )
    step = setup_uv_steps[0]
    assert step["uses"].startswith("astral-sh/setup-uv@v5"), (
        f"setup-uv must be @v5; got {step['uses']!r}"
    )
    with_block = step.get("with", {})
    assert with_block.get("enable-cache") is True, (
        f"setup-uv must set with.enable-cache: true; got with={with_block!r}"
    )
    assert with_block.get("cache-dependency-glob") == "code-review/uv.lock", (
        f"setup-uv must set cache-dependency-glob to code-review/uv.lock; "
        f"got {with_block.get('cache-dependency-glob')!r}"
    )


def test_concurrency_with_cancel_in_progress(workflow: dict[str, Any]) -> None:
    """CI runs are safe to cancel on new pushes — unlike release.yml which sets
    cancel-in-progress: false to protect partial publishes."""
    conc = workflow.get("concurrency", {})
    assert conc.get("group"), f"workflow-level concurrency.group missing; got {conc!r}"
    assert conc.get("cancel-in-progress") is True, (
        f"CI concurrency must set cancel-in-progress: true; got {conc!r}"
    )
