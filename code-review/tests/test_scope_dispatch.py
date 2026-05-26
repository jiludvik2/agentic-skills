from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.cli import app
from tests.conftest import FakeAnalyzer

REPO_ROOT = Path(__file__).parent.parent
REVIEWER_MD = REPO_ROOT / ".claude" / "skills" / "code-review" / "agents" / "reviewer.md"
SETUP = REPO_ROOT / "scripts" / "setup.sh"
PREFETCH = REPO_ROOT / "scripts" / "prefetch_caches.py"


def _reviewer_text() -> str:
    return REVIEWER_MD.read_text(encoding="utf-8")


def _section(text: str, header: str) -> str:
    import re

    m = re.search(rf"^(#+)\s*{re.escape(header)}", text, re.MULTILINE | re.IGNORECASE)
    assert m, f"missing section: {header}"
    level = len(m.group(1))
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def test_reviewer_md_documents_three_scopes() -> None:
    text = _reviewer_text().lower()
    for scope in ("lite", "standard", "full"):
        assert scope in text, f"bundled reviewer.md does not document scope '{scope}'"


def test_reviewer_md_lite_is_llm_only() -> None:
    lite = _section(_reviewer_text(), "lite").lower()
    assert "no" in lite and ("cli" in lite or "analyzer" in lite or "subprocess" in lite), (
        "lite section must state the analyzer CLI is not invoked"
    )


def test_reviewer_md_standard_full_invoke_cli() -> None:
    text = _reviewer_text()
    assert "code_review.cli" in text, "standard/full must reference the code_review.cli invocation"
    assert "--review-scope" in text, "standard/full must pass --review-scope"


def test_default_scope_is_lite() -> None:
    text = _reviewer_text().lower()
    assert "default" in text and "lite" in text, "reviewer.md must state the default scope is lite"


def test_cli_accepts_review_scope_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake", FakeAnalyzer)
    runner = CliRunner()
    for scope in ("lite", "standard", "full"):
        result = runner.invoke(
            app, ["--analyzer", "fake", "--target", ".", "--review-scope", scope]
        )
        assert result.exit_code == 0, f"{scope}: {result.output}"
    bad = runner.invoke(app, ["--analyzer", "fake", "--target", ".", "--review-scope", "bogus"])
    assert bad.exit_code != 0


def _write_neutralised_setup(skill: Path) -> Path:
    """Copy setup.sh into a synthetic skill tree with the network-dependent step neutralised."""
    (skill / "scripts").mkdir(parents=True)
    (skill / "agents").mkdir(parents=True)
    sh = skill / "scripts" / "setup.sh"
    text = SETUP.read_text(encoding="utf-8").replace("uv sync --frozen", "true", 1)
    sh.write_text(text, encoding="utf-8")
    sh.chmod(0o755)
    shutil.copy(PREFETCH, skill / "scripts" / "prefetch_caches.py")
    return sh


def _make_skill_tree(root: Path) -> Path:
    """Build a synthetic deployed-layout skill bundle under root/.claude/skills/code-review."""
    skill = root / ".claude" / "skills" / "code-review"
    _write_neutralised_setup(skill)
    (skill / "agents" / "reviewer.md").write_text(
        "# bundled reviewer\nlite standard full\n", encoding="utf-8"
    )
    return skill


def test_setup_installs_reviewer_into_host(tmp_path: Path) -> None:
    skill = _make_skill_tree(tmp_path)
    sh = skill / "scripts" / "setup.sh"
    src = skill / "agents" / "reviewer.md"

    r = subprocess.run(["bash", str(sh)], capture_output=True, text=True, cwd=skill)
    assert r.returncode == 0, r.stdout + r.stderr
    installed = tmp_path / ".claude" / "agents" / "reviewer.md"
    assert installed.exists(), "reviewer.md not installed into host .claude/agents/"
    assert installed.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")

    # second run: byte-identical (idempotent install)
    r2 = subprocess.run(["bash", str(sh)], capture_output=True, text=True, cwd=skill)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert installed.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_setup_install_fails_loud_without_project_root(tmp_path: Path) -> None:
    # skill tree with NO .claude ancestor
    skill = tmp_path / "standalone" / "code-review"
    sh = _write_neutralised_setup(skill)
    (skill / "agents" / "reviewer.md").write_text("x", encoding="utf-8")

    r = subprocess.run(["bash", str(sh)], capture_output=True, text=True, cwd=skill)
    assert r.returncode != 0
    combined = (r.stdout + r.stderr).lower()
    assert "host" in combined and "root" in combined, combined
