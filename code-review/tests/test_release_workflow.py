"""s2-t3: structural assertions on .github/workflows/release.yml — the
three-job split, OIDC scoping, official PyPA action usage, setup-uv@v5."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# release.yml lives at the monorepo root, one directory above code-review/.
WORKFLOW_PATH = (
    Path(__file__).parent.parent.parent / ".github" / "workflows" / "release.yml"
)


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    assert WORKFLOW_PATH.exists(), f"release workflow missing at {WORKFLOW_PATH}"
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "release.yml must parse as a mapping"
    return data


def test_workflow_has_three_jobs(workflow: dict[str, Any]) -> None:
    jobs = workflow.get("jobs", {})
    assert set(jobs.keys()) == {"build", "test-dist", "publish"}, (
        f"expected jobs {{build, test-dist, publish}}; got {sorted(jobs.keys())}"
    )


def test_job_dependency_chain(workflow: dict[str, Any]) -> None:
    jobs = workflow["jobs"]
    assert jobs["test-dist"].get("needs") == "build", (
        f"test-dist must `needs: build`; got {jobs['test-dist'].get('needs')!r}"
    )
    assert jobs["publish"].get("needs") == "test-dist", (
        f"publish must `needs: test-dist`; got {jobs['publish'].get('needs')!r}"
    )


def test_id_token_only_on_publish(workflow: dict[str, Any]) -> None:
    """OIDC privilege must be scoped to the publish job only."""
    assert "permissions" not in workflow or "id-token" not in workflow.get("permissions", {}), (
        "id-token must not be declared at workflow level; scope to publish job only"
    )
    jobs = workflow["jobs"]
    for job_name in ("build", "test-dist"):
        perms = jobs[job_name].get("permissions", {})
        assert "id-token" not in perms, (
            f"job {job_name!r} must not declare id-token; only publish gets OIDC"
        )
    publish_perms = jobs["publish"].get("permissions", {})
    assert publish_perms.get("id-token") == "write", (
        f"publish must declare permissions.id-token=write; got {publish_perms!r}"
    )


def test_publish_uses_official_pypa_action(workflow: dict[str, Any]) -> None:
    """Use pypa/gh-action-pypi-publish@release/v1 (the official action) so OIDC
    handling stays in PyPA's code, not in a uv publish step."""
    steps = workflow["jobs"]["publish"].get("steps", [])
    pypi_uses = [s.get("uses", "") for s in steps if isinstance(s, dict)]
    matches = [
        u for u in pypi_uses
        if u.startswith("pypa/gh-action-pypi-publish@release/v1")
    ]
    assert matches, (
        f"publish job must use pypa/gh-action-pypi-publish@release/v1; "
        f"got uses=[{pypi_uses!r}]"
    )


def test_setup_uv_uses_v5_with_cache(workflow: dict[str, Any]) -> None:
    """Upgrade from setup-uv@v3 to @v5 (automatic cache-key derivation)."""
    all_steps: list[dict[str, Any]] = []
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if isinstance(step, dict):
                all_steps.append(step)

    setup_uv_steps = [
        s for s in all_steps
        if str(s.get("uses", "")).startswith("astral-sh/setup-uv@")
    ]
    assert setup_uv_steps, "no astral-sh/setup-uv step found in any job"

    for step in setup_uv_steps:
        assert step["uses"].startswith("astral-sh/setup-uv@v5"), (
            f"setup-uv must be @v5; got {step['uses']!r}"
        )

    with_cache = [s for s in setup_uv_steps if s.get("with", {}).get("enable-cache") is True]
    assert with_cache, (
        "at least one astral-sh/setup-uv@v5 step must set with.enable-cache: true"
    )
    cache_glob_ok = any(
        s.get("with", {}).get("cache-dependency-glob") == "code-review/uv.lock"
        for s in with_cache
    )
    assert cache_glob_ok, (
        "setup-uv@v5 cache step must set cache-dependency-glob: code-review/uv.lock"
    )


def test_concurrency_block_preserved(workflow: dict[str, Any]) -> None:
    assert "concurrency" in workflow, "workflow-level concurrency block missing"
    assert workflow["concurrency"].get("group"), "concurrency.group must be set"


def test_tag_prefix_routing_preserved(workflow: dict[str, Any]) -> None:
    """The trigger glob must still include code-review-v* so sibling subprojects'
    tags don't fire this workflow."""
    # PyYAML parses bare `on:` as boolean True (YAML 1.1 quirk). Try both keys.
    on_block = workflow.get("on") or workflow.get(True)
    assert isinstance(on_block, dict), f"`on` block must be a mapping; got {on_block!r}"
    tags = on_block.get("push", {}).get("tags", [])
    assert "code-review-v*" in tags, (
        f"trigger tags must include 'code-review-v*'; got {tags!r}"
    )


def test_testpypi_routing_present(workflow: dict[str, Any]) -> None:
    """An -rc tag must route to TestPyPI; a non-rc tag to PyPI."""
    steps = workflow["jobs"]["publish"].get("steps", [])
    # Find any step that mentions test.pypi.org as the publish target (regardless
    # of whether it's a uv publish or the PyPA action with repository-url).
    repository_urls = [
        s.get("with", {}).get("repository-url", "")
        for s in steps if isinstance(s, dict)
    ]
    run_blocks = [
        s.get("run", "") for s in steps if isinstance(s, dict)
    ]
    testpypi_found = any("test.pypi.org" in (u or "") for u in repository_urls) or any(
        "test.pypi.org" in (r or "") for r in run_blocks
    )
    assert testpypi_found, "TestPyPI publish target missing from publish job"
