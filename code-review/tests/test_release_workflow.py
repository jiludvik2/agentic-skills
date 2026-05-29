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


def _setup_uv_steps_in(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        s for s in job.get("steps", [])
        if isinstance(s, dict)
        and str(s.get("uses", "")).startswith("astral-sh/setup-uv@")
    ]


def test_setup_uv_uses_v5_with_cache_on_build(workflow: dict[str, Any]) -> None:
    """setup-uv@v5 must be present and configured on `build` — that's where
    the uv.lock-driven cache benefit actually lands. publish operates on the
    downloaded artifact and must NOT install uv (no source-tree access)."""
    build_steps = _setup_uv_steps_in(workflow["jobs"]["build"])
    assert build_steps, "build job must include an astral-sh/setup-uv step"
    assert len(build_steps) == 1, (
        f"expected exactly one setup-uv step in build; got {len(build_steps)}"
    )

    step = build_steps[0]
    assert step["uses"].startswith("astral-sh/setup-uv@v5"), (
        f"build's setup-uv must be @v5; got {step['uses']!r}"
    )
    with_block = step.get("with", {})
    assert with_block.get("enable-cache") is True, (
        f"build's setup-uv must set with.enable-cache: true; got with={with_block!r}"
    )
    assert with_block.get("cache-dependency-glob") == "code-review/uv.lock", (
        f"build's setup-uv must set cache-dependency-glob to code-review/uv.lock; "
        f"got {with_block.get('cache-dependency-glob')!r}"
    )


def test_publish_does_not_install_uv(workflow: dict[str, Any]) -> None:
    """publish must operate on the downloaded artifact only — installing uv there
    would imply source-tree access and expand the OIDC-privileged blast radius."""
    publish_steps = _setup_uv_steps_in(workflow["jobs"]["publish"])
    assert not publish_steps, (
        f"publish must not install uv; OIDC blast radius should stay minimal. "
        f"Found: {publish_steps!r}"
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
