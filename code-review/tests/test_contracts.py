import dataclasses
import inspect

import pytest


def test_protocol_members_present():
    from code_review.contracts import Analyzer

    import typing

    hints = typing.get_type_hints(Analyzer)
    assert "name" in hints
    assert "kind" in hints
    assert "default_timeout_s" in hints
    assert "scope_restrictions" in hints
    members = dict(inspect.getmembers(Analyzer))
    assert "run" in members
    assert inspect.iscoroutinefunction(members["run"])


def test_analyzer_output_is_frozen_dataclass():
    from code_review.contracts import AnalyzerOutput

    assert dataclasses.is_dataclass(AnalyzerOutput)
    obj = AnalyzerOutput(sarif={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        obj.status = "error"  # type: ignore[misc]


def test_metric_set_fields():
    from code_review.contracts import MetricSet

    ms = MetricSet(per_file={}, per_class={}, coupling={})
    assert ms.per_file == {}
    assert ms.per_class == {}
    assert ms.coupling == {}


def test_review_request_target_paths_is_tuple():
    from code_review.contracts import ReviewRequest

    req = ReviewRequest(
        scope="standard",
        diff_range=None,
        target_paths=("src/foo.py",),
        languages=frozenset({"python"}),
        config={},
    )
    assert isinstance(req.target_paths, tuple)


def test_non_conforming_class_fails_protocol():
    from code_review.contracts import Analyzer

    class Bad:
        pass

    assert isinstance(Bad(), Analyzer) is False
