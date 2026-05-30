"""s6-t2: `polyreview install` — agent-independent skill-bundle install (ADR-0018).

Hermetic: $HOME (and CLAUDE_CONFIG_DIR) are monkeypatched to a tmp dir so target
resolution never touches the real user homes. The bundle source resolves via the
dev fallback (.claude/skills/code-review/) since the source tree has no wheel
_bundle/ — exercising the same copy path the installed command uses.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from code_review.bundle import BUNDLE_FILES
from code_review.cli import app

runner = CliRunner(capture="fd")

# Assets that must be present in an installed bundle (files + a dir spot-check).
_EXPECTED = [*BUNDLE_FILES, "semgrep-rules/security.yaml"]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return h


def _assert_bundle_at(dest: Path) -> None:
    assert dest.is_dir(), f"bundle dir missing: {dest}"
    for rel in _EXPECTED:
        assert (dest / rel).is_file(), f"missing bundle asset {rel} in {dest}"


def test_install_creates_neutral_dir_on_virgin_home(home: Path) -> None:
    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0, result.stdout
    _assert_bundle_at(home / ".agents" / "skills" / "code-review")


def test_install_default_targets_neutral_plus_present_homes(home: Path) -> None:
    (home / ".claude").mkdir()  # only claude home pre-exists
    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0, result.stdout
    _assert_bundle_at(home / ".agents" / "skills" / "code-review")
    _assert_bundle_at(home / ".claude" / "skills" / "code-review")
    assert not (home / ".copilot").exists()
    assert not (home / ".gemini").exists()


def test_install_agent_flag_scopes_target(home: Path) -> None:
    result = runner.invoke(app, ["install", "--agent", "copilot"])
    assert result.exit_code == 0, result.stdout
    _assert_bundle_at(home / ".copilot" / "skills" / "code-review")
    # No other target written.
    assert not (home / ".agents").exists()
    assert not (home / ".claude").exists()
    assert not (home / ".gemini").exists()


def test_install_agent_flag_accepts_comma_list(home: Path) -> None:
    result = runner.invoke(app, ["install", "--agent", "claude,copilot"])
    assert result.exit_code == 0, result.stdout
    _assert_bundle_at(home / ".claude" / "skills" / "code-review")
    _assert_bundle_at(home / ".copilot" / "skills" / "code-review")
    assert not (home / ".agents").exists()


def test_install_unknown_agent_errors(home: Path) -> None:
    result = runner.invoke(app, ["install", "--agent", "emacs"])
    assert result.exit_code == 1
    assert "unknown agent target" in result.stderr


def test_install_all_writes_every_registry_dir(home: Path) -> None:
    result = runner.invoke(app, ["install", "--all"])
    assert result.exit_code == 0, result.stdout
    for base in (".agents", ".claude", ".copilot", ".gemini"):
        _assert_bundle_at(home / base / "skills" / "code-review")


def test_install_claude_honours_config_dir_env(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = tmp_path / "custom-claude"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(custom))
    result = runner.invoke(app, ["install", "--agent", "claude"])
    assert result.exit_code == 0, result.stdout
    _assert_bundle_at(custom / "skills" / "code-review")
    assert not (home / ".claude").exists()


def test_install_idempotent_without_force(home: Path) -> None:
    first = runner.invoke(app, ["install", "--agent", "agents"])
    assert first.exit_code == 0, first.stdout
    dest = home / ".agents" / "skills" / "code-review"
    # Mutate an installed file (not the SKILL.md marker); a no-op re-install must
    # NOT overwrite it. Using package.json keeps the marker check passing so the
    # second run resolves to "skipped", not "refused".
    sentinel = dest / "package.json"
    sentinel.write_text("USER-EDITED", encoding="utf-8")
    second = runner.invoke(app, ["install", "--agent", "agents"])
    assert second.exit_code == 0, second.stdout
    assert "skipped" in second.stdout
    assert sentinel.read_text(encoding="utf-8") == "USER-EDITED"


def test_install_force_refreshes(home: Path) -> None:
    runner.invoke(app, ["install", "--agent", "agents"])
    dest = home / ".agents" / "skills" / "code-review"
    # A stale file from a prior bundle version must not survive a --force refresh.
    stale = dest / "STALE-LEFTOVER.txt"
    stale.write_text("old", encoding="utf-8")
    result = runner.invoke(app, ["install", "--agent", "agents", "--force"])
    assert result.exit_code == 0, result.stdout
    assert "refreshed" in result.stdout
    assert not stale.exists(), "remove-then-copy must drop stale files"
    _assert_bundle_at(dest)


def test_install_leaves_reviewer_and_sibling_skills_untouched(home: Path) -> None:
    claude = home / ".claude"
    (claude / "agents").mkdir(parents=True)
    reviewer = claude / "agents" / "reviewer.md"
    reviewer.write_text("REVIEWER", encoding="utf-8")
    (claude / "skills" / "other").mkdir(parents=True)
    other = claude / "skills" / "other" / "SKILL.md"
    other.write_text("OTHER-SKILL", encoding="utf-8")

    result = runner.invoke(app, ["install", "--agent", "claude"])
    assert result.exit_code == 0, result.stdout

    assert reviewer.read_text(encoding="utf-8") == "REVIEWER"
    assert other.read_text(encoding="utf-8") == "OTHER-SKILL"
    _assert_bundle_at(claude / "skills" / "code-review")


def test_install_refuses_foreign_dir_at_target(home: Path) -> None:
    # A non-bundle dir sitting at our target path must not be overwritten.
    foreign = home / ".agents" / "skills" / "code-review"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("name: someone-else\n", encoding="utf-8")
    result = runner.invoke(app, ["install", "--agent", "agents"])
    assert result.exit_code == 1
    assert "refused" in result.stdout
    assert (foreign / "SKILL.md").read_text(encoding="utf-8") == "name: someone-else\n"


def test_install_refuses_marker_near_collision(home: Path) -> None:
    # A foreign SKILL.md whose name *contains* "code-review" as a prefix
    # (`code-reviewer`) must NOT pass the marker guard — the check is anchored to a
    # full frontmatter line, so it cannot be tricked into rmtree-ing a neighbour.
    foreign = home / ".agents" / "skills" / "code-review"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text(
        "---\nname: code-reviewer\n---\n", encoding="utf-8"
    )
    result = runner.invoke(app, ["install", "--agent", "agents", "--force"])
    assert result.exit_code == 1
    assert "refused" in result.stdout
    assert (foreign / "SKILL.md").read_text(encoding="utf-8") == (
        "---\nname: code-reviewer\n---\n"
    )


def test_install_reports_targets_and_cache_hint(home: Path) -> None:
    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0, result.stdout
    # Each written skills dir is listed.
    assert str(home / ".agents" / "skills" / "code-review") in result.stdout
    # And the cache-provisioning follow-up is named.
    assert "setup.sh" in result.stdout


def test_review_run_still_invokable_after_restructure() -> None:
    # The review path survives the subcommand restructure under its `run` spelling.
    result = runner.invoke(app, ["run", "--capabilities"])
    assert result.exit_code == 0, result.stdout
    assert '"analyzers"' in result.stdout
