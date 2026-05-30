import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
ESLINT_FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-eslint"
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
        patch("code_review.adapters.eslint.has_js_files", return_value=True),
        patch("code_review.adapters.eslint._has_eslint_config", return_value=True),
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
        patch("code_review.adapters.eslint.has_js_files", return_value=True),
        patch("code_review.adapters.eslint._has_eslint_config", return_value=True),
        patch("code_review.adapters.eslint.run_subprocess", new=fake_run),
    ):
        output = await EslintAdapter().run(request)

    assert output.status == "ok"
    env = captured["env"]
    assert isinstance(env, dict) and "NODE_PATH" in env, "adapter must pass NODE_PATH in env"
    assert str(node_modules_dir()) in env["NODE_PATH"]


async def test_eslint_anchors_cwd_at_existing_directory_for_missing_file() -> None:
    """The adapter anchors eslint's cwd at the targets' directory. When a single
    target path is not itself an existing directory (a single file, or a deleted
    file from a diff), the cwd must still be an existing directory (the parent) —
    otherwise the subprocess fails on a non-existent cwd instead of letting eslint
    report the missing file."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    captured: dict[str, object] = {}

    async def fake_run(*cmd: str, **kwargs: object) -> SubprocessResult:
        captured["cwd"] = kwargs.get("cwd")
        sarif = json.dumps(
            {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "ESLint"}}, "results": []}]}
        ).encode()
        return SubprocessResult(sarif, b"", 0)

    # Parent dir exists; the file itself does not (e.g. a diff that deletes it).
    missing = str(ESLINT_FIXTURE / "no_such_file.js")
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(missing,), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess", new=fake_run),
    ):
        await EslintAdapter().run(request)

    cwd = captured["cwd"]
    assert isinstance(cwd, str) and Path(cwd).is_dir(), f"cwd must be an existing dir, got {cwd!r}"


async def test_eslint_no_flat_config_is_unavailable(tmp_path: Path) -> None:
    """A JS target with no eslint.config.* (and no .eslintrc) anywhere upward is
    'nothing to run here', not a failure: status unavailable, the reason names the
    missing flat config, and eslint is never invoked (ADR-0019)."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    (tmp_path / "app.js").write_text("const x = 1;\n")
    invoked = False

    async def fake_run(*cmd: str, **kwargs: object) -> SubprocessResult:
        nonlocal invoked
        invoked = True
        return SubprocessResult(b"", b"", 0)

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess", new=fake_run),
    ):
        output = await EslintAdapter().run(request)
    assert output.status == "unavailable", output.error
    assert "config" in (output.error or "").lower()
    assert not invoked, "eslint must not be invoked when there is no config to run"


async def test_eslint_with_flat_config_lints(tmp_path: Path) -> None:
    """Regression: a target that DOES carry a flat config still lints — the
    no-config skip must not short-circuit the normal path."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    (tmp_path / "app.js").write_text("const x = 1;\n")
    fake_sarif = json.dumps(
        {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "ESLint"}}, "results": []}]}
    ).encode()
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess",
              new=AsyncMock(return_value=SubprocessResult(fake_sarif, b"", 1))),
    ):
        output = await EslintAdapter().run(request)
    assert output.status == "ok", output.error
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "ESLint"


async def test_eslint_unexpected_failure_is_error(tmp_path: Path) -> None:
    """With a config present, a genuine non-zero eslint exit is still surfaced as
    error — unavailable is reserved for 'nothing to run', never a real crash."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    (tmp_path / "app.js").write_text("const x = 1;\n")
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess",
              new=AsyncMock(return_value=SubprocessResult(b"", b"Oops: real eslint crash\n", 2))),
    ):
        output = await EslintAdapter().run(request)
    assert output.status == "error", output.error
    assert "exited 2" in (output.error or "")


async def test_eslint_unavailable_without_js(tmp_path: Path) -> None:
    """A target tree with no JS/TS files at all is 'nothing to run' — reported as
    unavailable (distinct reason from the no-flat-config case) and eslint is never
    invoked (ADR-0019, s0-t2)."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    (tmp_path / "app.py").write_text("x = 1\n")
    invoked = False

    async def fake_run(*cmd: str, **kwargs: object) -> SubprocessResult:
        nonlocal invoked
        invoked = True
        return SubprocessResult(b"", b"", 0)

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess", new=fake_run),
    ):
        output = await EslintAdapter().run(request)
    assert output.status == "unavailable", output.error
    assert "javascript" in (output.error or "").lower()
    assert not invoked, "eslint must not be invoked when there is no JS to analyse"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("eslint") is None,
    reason="eslint not in node_modules (run scripts/setup.sh)",
)
async def test_eslint_integration_single_file_target() -> None:
    """A single existing file target (e.g. `--target path/to/file.js`) from a
    foreign cwd: the adapter anchors eslint's cwd at the file's directory so the
    project's flat config is discovered and the file falls within the base path."""
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=(str(ESLINT_FIXTURE / "lint_me.js"),),
        languages=frozenset({"javascript"}), config={},
    )
    output = await EslintAdapter().run(request)
    assert output.status == "ok", output.error
    results = output.sarif["runs"][0]["results"]
    assert len(results) >= 1, "expected eslint to flag the planted violations"


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
async def test_eslint_integration_detects_console_log() -> None:
    """Pointed at a JS project dir that ships its own flat config, the adapter
    discovers that config (it anchors eslint's cwd at the target root) and reports
    the planted rule violations — no external NODE_PATH, no manual cwd change, same
    `target_paths=(str(FIXTURE),)` idiom as the depcruiser/jscpd integration tests."""
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(ESLINT_FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await EslintAdapter().run(request)
    assert output.status == "ok", output.error
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
    results = output.sarif["runs"][0]["results"]
    assert len(results) >= 1, "expected eslint to flag the planted violations"
    rule_ids = {r.get("ruleId") for r in results}
    assert rule_ids & {"no-console", "no-unused-vars"}, rule_ids
