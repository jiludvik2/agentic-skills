from __future__ import annotations

import importlib.resources
import json

import jsonschema
import pytest

_PKG = importlib.resources.files("code_review")

_BUNDLED_JSON = [
    "capabilities.json",
    "schemas/capabilities.json",
    "schemas/review-request.json",
    "schemas/review-response.json",
    "schemas/sarif-2.1.0.json",
]

_SCHEMA_JSON = [p for p in _BUNDLED_JSON if p.startswith("schemas/")]


def _traverse(rel_path: str) -> importlib.resources.abc.Traversable:
    resource = _PKG
    for part in rel_path.split("/"):
        resource = resource.joinpath(part)
    return resource


@pytest.mark.parametrize("rel_path", _BUNDLED_JSON)
def test_bundled_json_is_reachable(rel_path: str) -> None:
    resource = _traverse(rel_path)
    assert resource.is_file(), f"{rel_path} not reachable via importlib.resources"


@pytest.mark.parametrize("rel_path", _BUNDLED_JSON)
def test_bundled_json_loads(rel_path: str) -> None:
    resource = _traverse(rel_path)
    data = json.loads(resource.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


@pytest.mark.parametrize("rel_path", _SCHEMA_JSON)
def test_schema_is_valid_json_schema(rel_path: str) -> None:
    resource = _traverse(rel_path)
    schema = json.loads(resource.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
