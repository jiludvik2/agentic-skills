"""Shared test helpers for parsing GitHub Actions workflow YAML.

Lives in tests/ rather than code_review/ because these helpers are only useful
to test code and never imported by production paths.
"""
from __future__ import annotations

from typing import Any


def workflow_on_block(workflow: dict[str, Any]) -> dict[str, Any]:
    """Return the workflow's `on:` block as a mapping.

    PyYAML's YAML 1.1 safe-loader maps the bare key `on` to Python `True`
    (the boolean), since `on` is a YAML 1.1 truthy literal. The canonical
    GitHub Actions syntax is `on:` (bare), so we accept both forms here so
    individual test modules don't each need to repeat the quirk handler.
    """
    block = workflow.get("on") or workflow.get(True)
    assert isinstance(block, dict), f"`on` block must be a mapping; got {block!r}"
    return block
