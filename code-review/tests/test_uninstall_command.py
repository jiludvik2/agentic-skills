"""s7-t0: `polyreview uninstall` — agent-independent skill-bundle removal (ADR-0018 §5).

Hermetic: $HOME (and CLAUDE_CONFIG_DIR) are monkeypatched to a tmp dir so target
resolution never touches the real user homes. "Installed" state is built either by
invoking the s6 install command (the round-trip test) or by seeding the marker file
directly (the unit cases). The marker check is the load-bearing safety guard: a
directory that fails it is never removed.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from code_review.cli import app

runner = CliRunner(capture="fd")


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return h


def _seed_bundle(skills_dir: Path) -> Path:
    """Create a minimal but marker-valid installed bundle at <skills-dir>/code-review/."""
    dest = skills_dir / "code-review"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("---\nname: code-review\n---\n", encoding="utf-8")
    (dest / "package.json").write_text("{}\n", encoding="utf-8")
    return dest


def test_uninstall_removes_from_all_installed_targets(home: Path) -> None:
    agents = _seed_bundle(home / ".agents" / "skills")
    claude = _seed_bundle(home / ".claude" / "skills")
    result = runner.invoke(app, ["uninstall"])
    assert result.exit_code == 0, result.stdout
    assert not agents.exists()
    assert not claude.exists()


def test_uninstall_agent_flag_scopes_removal(home: Path) -> None:
    agents = _seed_bundle(home / ".agents" / "skills")
    claude = _seed_bundle(home / ".claude" / "skills")
    result = runner.invoke(app, ["uninstall", "--agent", "claude"])
    assert result.exit_code == 0, result.stdout
    assert not claude.exists()
    assert agents.exists(), "agents copy must remain when only --agent claude is uninstalled"


def test_uninstall_noop_when_absent(home: Path) -> None:
    result = runner.invoke(app, ["uninstall"])
    assert result.exit_code == 0, result.stdout
    assert "nothing to uninstall" in result.stdout


def test_uninstall_refuses_unmarked_dir(home: Path) -> None:
    foreign = home / ".agents" / "skills" / "code-review"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("name: someone-else\n", encoding="utf-8")
    result = runner.invoke(app, ["uninstall", "--agent", "agents"])
    assert result.exit_code == 1
    assert "marker" in result.stderr
    assert foreign.is_dir(), "an unmarked dir must be left intact"
    assert (foreign / "SKILL.md").read_text(encoding="utf-8") == "name: someone-else\n"


def test_uninstall_refusal_does_not_skip_other_targets(home: Path) -> None:
    # AC4: a refusal on one target must not silently skip the others — the clean
    # target is still removed and the refused one survives, run exits non-zero.
    good = _seed_bundle(home / ".claude" / "skills")
    bad = home / ".agents" / "skills" / "code-review"
    bad.mkdir(parents=True)
    (bad / "SKILL.md").write_text("name: someone-else\n", encoding="utf-8")

    result = runner.invoke(app, ["uninstall", "--all"])
    assert result.exit_code == 1
    assert not good.exists(), "the marked bundle must still be removed"
    assert bad.is_dir(), "the unmarked dir must be refused, not removed"
    assert "marker" in result.stderr


def test_uninstall_leaves_reviewer_and_siblings(home: Path) -> None:
    claude = home / ".claude"
    (claude / "agents").mkdir(parents=True)
    reviewer = claude / "agents" / "reviewer.md"
    reviewer.write_text("REVIEWER", encoding="utf-8")
    (claude / "skills" / "other").mkdir(parents=True)
    other = claude / "skills" / "other" / "SKILL.md"
    other.write_text("OTHER-SKILL", encoding="utf-8")
    bundle = _seed_bundle(claude / "skills")

    result = runner.invoke(app, ["uninstall", "--agent", "claude"])
    assert result.exit_code == 0, result.stdout

    assert not bundle.exists(), "only the bundle should be removed"
    assert reviewer.read_text(encoding="utf-8") == "REVIEWER"
    assert other.read_text(encoding="utf-8") == "OTHER-SKILL"
    assert (claude / "skills").is_dir(), "the skills dir itself must survive"


def test_uninstall_removes_nested_bundle_tree(home: Path) -> None:
    # The destructive path is a recursive rmtree: a bundle with a subdir (e.g. the
    # vendored semgrep-rules/) must be removed whole, and the action echoed.
    dest = _seed_bundle(home / ".agents" / "skills")
    (dest / "semgrep-rules").mkdir()
    (dest / "semgrep-rules" / "security.yaml").write_text("rules: []\n", encoding="utf-8")
    result = runner.invoke(app, ["uninstall", "--agent", "agents"])
    assert result.exit_code == 0, result.stdout
    assert not dest.exists()
    assert "removed" in result.stdout


def test_uninstall_mixed_present_and_absent(home: Path) -> None:
    # One target installed, another absent: the present bundle is removed, the run
    # exits 0, and "nothing to uninstall" is NOT printed (something was removed).
    claude = _seed_bundle(home / ".claude" / "skills")
    result = runner.invoke(app, ["uninstall", "--agent", "claude,copilot"])
    assert result.exit_code == 0, result.stdout
    assert not claude.exists()
    assert "removed" in result.stdout
    assert "nothing to uninstall" not in result.stdout


def test_install_uninstall_round_trip(home: Path) -> None:
    # Make claude + copilot homes present so the default install is multi-target.
    (home / ".claude").mkdir()
    (home / ".copilot").mkdir()

    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0, install_result.stdout
    # Sanity: the install placed at least one bundle.
    assert list(home.rglob("code-review")), "install should have written bundles"

    uninstall_result = runner.invoke(app, ["uninstall"])
    assert uninstall_result.exit_code == 0, uninstall_result.stdout
    # No orphaned bundle anywhere under the home after the round-trip.
    assert not list(home.rglob("code-review")), "uninstall must remove every bundle"
