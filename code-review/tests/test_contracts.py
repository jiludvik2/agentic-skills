import inspect


def test_protocol_members_present() -> None:
    import typing

    from code_review.contracts import Analyzer

    hints = typing.get_type_hints(Analyzer)
    assert "name" in hints
    assert "kind" in hints
    assert "default_timeout_s" in hints
    assert "scope_restrictions" in hints
    members = dict(inspect.getmembers(Analyzer))
    assert "run" in members
    assert inspect.iscoroutinefunction(members["run"])


def test_review_request_target_paths_is_tuple() -> None:
    from code_review.contracts import ReviewRequest

    req = ReviewRequest(
        scope="standard",
        diff_range=None,
        target_paths=("src/foo.py",),
        languages=frozenset({"python"}),
        config={},
    )
    assert isinstance(req.target_paths, tuple)


def test_non_conforming_class_fails_protocol() -> None:
    from code_review.contracts import Analyzer

    class Bad:
        pass

    assert isinstance(Bad(), Analyzer) is False
