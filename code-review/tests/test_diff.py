import subprocess
from pathlib import Path


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _make_repo_with_two_commits(root: Path) -> None:
    _git(["init"], root)
    _git(["config", "user.email", "test@test.com"], root)
    _git(["config", "user.name", "Test"], root)
    (root / "file_a.py").write_text("# a")
    _git(["add", "file_a.py"], root)
    _git(["commit", "-m", "add file_a"], root)
    (root / "file_b.py").write_text("# b")
    _git(["add", "file_b.py"], root)
    _git(["commit", "-m", "add file_b"], root)


async def test_resolve_diff_paths_returns_changed_files(tmp_path: Path):
    from code_review.diff import resolve_diff_paths

    _make_repo_with_two_commits(tmp_path)
    result = await resolve_diff_paths(tmp_path, "HEAD~1..HEAD")
    assert result == ("file_b.py",)


async def test_resolve_diff_paths_empty_range(tmp_path: Path):
    from code_review.diff import resolve_diff_paths

    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@test.com"], tmp_path)
    _git(["config", "user.name", "Test"], tmp_path)
    (tmp_path / "file.py").write_text("# file")
    _git(["add", "."], tmp_path)
    _git(["commit", "-m", "initial"], tmp_path)

    result = await resolve_diff_paths(tmp_path, "HEAD..HEAD")
    assert result == ()
