"""Tests for aligning Weblate review branches after translation sync."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def load_align_module(repo_root: Path):
    """Load the branch alignment helper as a module."""

    module_path = repo_root / "scripts" / "ci" / "align_weblate_review_branch.py"
    spec = importlib.util.spec_from_file_location("align_weblate_review_branch", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_align_creates_missing_weblate_branch(repo_root: Path, tmp_path: Path) -> None:
    """A target branch sync should initialize the matching Weblate review branch."""

    module = load_align_module(repo_root)
    repo = initialize_translation_repo(tmp_path)

    result = module.align_weblate_review_branch(
        repo=repo,
        target_branch="translation/v1.30.1",
        weblate_branch="weblate/v1.30.1",
    )

    assert result.action == "created"
    assert remote_branch_revision(repo, "weblate/v1.30.1") == git_output(
        repo,
        "rev-parse",
        "translation/v1.30.1",
    )


def test_align_updates_weblate_branch_when_it_is_ancestor(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """A stale Weblate branch can be safely moved to the validated target HEAD."""

    module = load_align_module(repo_root)
    repo = initialize_translation_repo(tmp_path)
    git(repo, "push", "origin", "master:refs/heads/weblate/v1.30.1")

    result = module.align_weblate_review_branch(
        repo=repo,
        target_branch="translation/v1.30.1",
        weblate_branch="weblate/v1.30.1",
    )

    assert result.action == "updated"
    assert remote_branch_revision(repo, "weblate/v1.30.1") == git_output(
        repo,
        "rev-parse",
        "translation/v1.30.1",
    )


def test_align_refuses_unpromoted_weblate_changes(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The helper must not overwrite Weblate commits that are not in the target branch."""

    module = load_align_module(repo_root)
    repo = initialize_translation_repo(tmp_path)
    git(repo, "checkout", "-B", "weblate-local", "master")
    (repo / "weblate.txt").write_text("unpromoted Weblate edit\n", encoding="utf-8")
    git(repo, "add", "weblate.txt")
    git(repo, "commit", "-m", "unpromoted Weblate edit")
    git(repo, "push", "origin", "HEAD:refs/heads/weblate/v1.30.1")
    previous_review_revision = remote_branch_revision(repo, "weblate/v1.30.1")
    git(repo, "checkout", "translation/v1.30.1")

    with pytest.raises(SystemExit, match="unpromoted changes"):
        module.align_weblate_review_branch(
            repo=repo,
            target_branch="translation/v1.30.1",
            weblate_branch="weblate/v1.30.1",
        )

    assert remote_branch_revision(repo, "weblate/v1.30.1") == previous_review_revision


def initialize_translation_repo(tmp_path: Path) -> Path:
    """Create a small translation repository with a bare origin."""

    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    git(tmp_path, "init", "--bare", str(origin))
    git(tmp_path, "init", "--initial-branch=master", str(repo))
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "remote", "add", "origin", str(origin))
    (repo / "README.md").write_text("control branch\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "initial commit")
    git(repo, "push", "-u", "origin", "master")

    git(repo, "checkout", "-b", "translation/v1.30.1")
    (repo / "translation.txt").write_text("validated translation\n", encoding="utf-8")
    git(repo, "add", "translation.txt")
    git(repo, "commit", "-m", "validated translation")
    git(repo, "push", "-u", "origin", "translation/v1.30.1")
    return repo


def remote_branch_revision(repo: Path, branch: str) -> str:
    """Return a remote branch revision."""

    output = git_output(repo, "ls-remote", "--heads", "origin", branch)
    return output.split()[0]


def git(cwd: Path, *args: str) -> None:
    """Run git with inherited output."""

    subprocess.run(["git", *args], cwd=cwd, check=True)


def git_output(cwd: Path, *args: str) -> str:
    """Run git and return stdout."""

    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
