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


async def test_resolve_diff_paths_returns_changed_files(tmp_path: Path) -> None:
    from code_review.diff import resolve_diff_paths

    _make_repo_with_two_commits(tmp_path)
    result = await resolve_diff_paths(tmp_path, "HEAD~1..HEAD")
    # resolve_diff_paths returns absolute paths anchored on the repo root
    assert result == (str(tmp_path / "file_b.py"),)


async def test_resolve_diff_paths_empty_range(tmp_path: Path) -> None:
    from code_review.diff import resolve_diff_paths

    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@test.com"], tmp_path)
    _git(["config", "user.name", "Test"], tmp_path)
    (tmp_path / "file.py").write_text("# file")
    _git(["add", "."], tmp_path)
    _git(["commit", "-m", "initial"], tmp_path)

    result = await resolve_diff_paths(tmp_path, "HEAD..HEAD")
    assert result == ()


async def test_diff_paths_resolve_from_subdir(tmp_path: Path) -> None:
    """Paths returned by resolve_diff_paths resolve to real files when launched from a subdir."""
    from code_review.diff import get_repo_root, resolve_diff_paths

    # Repo with a file nested in a subdirectory
    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@test.com"], tmp_path)
    _git(["config", "user.name", "Test"], tmp_path)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "module.py").write_text("# base")
    _git(["add", "pkg/module.py"], tmp_path)
    _git(["commit", "-m", "initial"], tmp_path)
    (pkg / "module.py").write_text("# changed")
    _git(["add", "pkg/module.py"], tmp_path)
    _git(["commit", "-m", "change module"], tmp_path)

    # Discover repo root from the subdirectory (as the CLI does from its cwd)
    repo_root = await get_repo_root(pkg)
    result = await resolve_diff_paths(repo_root, "HEAD~1..HEAD")

    assert len(result) == 1
    assert all(Path(p).exists() for p in result)


async def test_repo_root_discovery_falls_back_outside_git(tmp_path: Path) -> None:
    """get_repo_root returns cwd unchanged when not inside a git repo."""
    from code_review.diff import get_repo_root

    root = await get_repo_root(tmp_path)
    assert root == tmp_path
