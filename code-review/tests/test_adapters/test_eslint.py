import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"
SKILL_ROOT = Path(__file__).parent.parent.parent / ".claude" / "skills" / "code-review"


def test_eslint_protocol_conformance() -> None:
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import Analyzer

    assert isinstance(EslintAdapter(), Analyzer)
    assert EslintAdapter.name == "eslint"
    assert EslintAdapter.node_tool == "eslint"


async def test_eslint_returns_error_when_binary_absent(tmp_path: Path) -> None:
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    with patch("code_review.adapters.eslint.node_binary", return_value=None):
        request = ReviewRequest(scope="per-task", diff_range=None,
                                target_paths=(str(tmp_path),),
                                languages=frozenset(), config={})
        output = await EslintAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_eslint_empty_target_paths() -> None:
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    with patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")):
        output = await EslintAdapter().run(request)
    assert output.status == "ok"


async def test_eslint_parses_sarif_stdout() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = json.dumps({
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "ESLint"}}, "results": []}],
    }).encode()

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=("src/",), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess",
              new=AsyncMock(return_value=SubprocessResult(fake_sarif, b"", 0))),
    ):
        output = await EslintAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "ESLint"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)


async def test_eslint_sets_node_path_to_vendored_modules() -> None:
    """The formatter (@microsoft/eslint-formatter-sarif) must resolve regardless
    of the adapter's cwd; the adapter guarantees this by exporting NODE_PATH
    pointed at the vendored node_modules before invoking eslint."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest
    from code_review.paths import node_modules_dir

    captured: dict[str, object] = {}

    async def fake_run(*cmd: str, **kwargs: object) -> SubprocessResult:
        captured["env"] = kwargs.get("env")
        sarif = json.dumps(
            {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "ESLint"}}, "results": []}]}
        ).encode()
        return SubprocessResult(sarif, b"", 0)

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=("src/",), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess", new=fake_run),
    ):
        output = await EslintAdapter().run(request)

    assert output.status == "ok"
    env = captured["env"]
    assert isinstance(env, dict) and "NODE_PATH" in env, "adapter must pass NODE_PATH in env"
    assert str(node_modules_dir()) in env["NODE_PATH"]


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("eslint") is None,
    reason="eslint not in node_modules (run scripts/setup.sh)",
)
async def test_eslint_formatter_resolves_from_foreign_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run the adapter from a cwd outside the skill root and confirm the SARIF
    formatter (@microsoft/eslint-formatter-sarif) still resolves — no
    module-not-found / 'Cannot find formatter'. A self-contained flat config +
    file lives in the foreign cwd so eslint reaches the formatting stage without
    tripping config-discovery (that robustness is F8/s4, out of scope here)."""
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    # Anchor cache_root() at the real skill root, then run from an unrelated cwd
    # that has no node_modules — so the formatter can only resolve via the
    # adapter's NODE_PATH, not via cwd-relative module resolution.
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(SKILL_ROOT))
    (tmp_path / "eslint.config.mjs").write_text(
        "export default [{ rules: { 'no-unused-vars': 'error' } }];\n"
    )
    (tmp_path / "lint_me.js").write_text("const unused = 1;\nexport const used = 2;\n")
    monkeypatch.chdir(tmp_path)
    request = ReviewRequest(
        scope="per-task", diff_range=None, target_paths=("lint_me.js",),
        languages=frozenset({"javascript"}), config={},
    )
    output = await EslintAdapter().run(request)
    err = (output.error or "").lower()
    assert "cannot find" not in err and "formatter" not in err, output.error
    assert output.status == "ok", output.error


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("eslint") is None,
    reason="eslint not in node_modules (run scripts/setup.sh)",
)
@pytest.mark.xfail(
    reason="eslint config discovery on un-scaffolded fixtures is F8/s4; this "
    "fixture ships no eslint.config.* so eslint v9 errors before linting. "
    "s1-t2 only guarantees formatter resolution (see test above).",
    strict=True,
)
async def test_eslint_integration_detects_console_log() -> None:
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await EslintAdapter().run(request)
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
