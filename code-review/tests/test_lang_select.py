from __future__ import annotations


def test_python_only_selects_python_adapters() -> None:
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"python"}))
    assert "bandit" in result
    assert "vulture" in result
    assert "radon" in result
    assert "eslint" not in result
    assert "knip" not in result


def test_typescript_selects_js_adapters() -> None:
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"typescript"}))
    assert "eslint" in result
    assert "jscpd" in result
    assert "bandit" not in result
    assert "radon" not in result


def test_mixed_selects_all_relevant() -> None:
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"python", "typescript"}))
    assert "bandit" in result
    assert "eslint" in result
    assert "gitleaks" in result  # language-agnostic


def test_javascript_selects_jscomplexity() -> None:
    from code_review.lang_select import select_adapters

    assert "jscomplexity" in select_adapters(frozenset({"javascript"}))
    assert "jscomplexity" not in select_adapters(frozenset({"python"}))


def test_unknown_language_returns_common_only() -> None:
    from code_review.lang_select import select_adapters

    result = select_adapters(frozenset({"rust"}))
    assert "gitleaks" in result
    assert "bandit" not in result
    assert "eslint" not in result
