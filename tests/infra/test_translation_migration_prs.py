"""Tests for migration PR automation helpers."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def test_create_pr_requires_push(repo_root: Path, monkeypatch) -> None:
    """PR creation should fail early when no remote head branch will be pushed."""

    module = _load_migration_pr_module(repo_root)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_translation_migration_prs.py",
            "--tooling-root",
            str(repo_root),
            "--source-version",
            "v1.30.1",
            "--create-pr",
        ],
    )

    with pytest.raises(SystemExit, match="--create-pr requires --push"):
        module.main()


def test_missing_clean_artifact_root_fails_early(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A typo in the downloaded artifact path should not fail later per target."""

    module = _load_migration_pr_module(repo_root)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_translation_migration_prs.py",
            "--tooling-root",
            str(repo_root),
            "--source-version",
            "v1.30.1",
            "--clean-artifact-root",
            str(tmp_path / "missing"),
        ],
    )

    with pytest.raises(SystemExit, match="--clean-artifact-root does not exist"):
        module.main()


def test_add_detached_remote_worktree_ignores_open_local_branch(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Migration checkouts should not fail when a branch is open elsewhere."""

    module = _load_migration_pr_module(repo_root)
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    open_worktree = tmp_path / "open-branch"
    detached_worktree = tmp_path / "detached"

    _run_git(tmp_path, "init", "--bare", str(origin))
    _run_git(tmp_path, "init", "--initial-branch=master", str(repo))
    _run_git(repo, "config", "user.name", "Test User")
    _run_git(repo, "config", "user.email", "test@example.invalid")
    _run_git(repo, "remote", "add", "origin", str(origin))
    (repo / "README.md").write_text("public template repo\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-m", "initial")
    _run_git(repo, "push", "-u", "origin", "master")
    _run_git(repo, "checkout", "-b", "sync/v1.30.1")
    _run_git(repo, "commit", "--allow-empty", "-m", "version branch")
    _run_git(repo, "push", "-u", "origin", "sync/v1.30.1")
    _run_git(repo, "checkout", "master")
    _run_git(repo, "worktree", "add", str(open_worktree), "sync/v1.30.1")

    try:
        module.add_detached_remote_worktree(
            repo=repo,
            checkout=detached_worktree,
            branch="sync/v1.30.1",
        )

        assert _git_symbolic_ref(detached_worktree) is None
        assert _git_show(detached_worktree, "HEAD:README.md") == "public template repo\n"
    finally:
        _run_git(repo, "worktree", "remove", "--force", str(open_worktree))
        if detached_worktree.exists():
            _run_git(repo, "worktree", "remove", "--force", str(detached_worktree))


def test_add_detached_remote_worktree_reports_missing_branch(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Missing remote branches should produce a direct, actionable error."""

    module = _load_migration_pr_module(repo_root)
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"

    _run_git(tmp_path, "init", "--bare", str(origin))
    _run_git(tmp_path, "init", "--initial-branch=master", str(repo))
    _run_git(repo, "remote", "add", "origin", str(origin))

    with pytest.raises(SystemExit, match="Remote branch does not exist"):
        module.add_detached_remote_worktree(
            repo=repo,
            checkout=tmp_path / "detached",
            branch="sync/v9.99.9",
        )


def test_manual_pull_request_url_uses_github_environment(
    repo_root: Path,
    monkeypatch,
) -> None:
    """Manual fallback URLs should point at a compare page with both branches."""

    module = _load_migration_pr_module(repo_root)
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "ThreeMonth03/example")

    url = module.manual_pull_request_url(
        base_branch="sync/v1.29.1",
        head_branch="automation/migrate-v1.30.1-to-v1.29.1",
    )

    assert url == (
        "https://github.com/ThreeMonth03/example/compare/"
        "sync%2Fv1.29.1...automation%2Fmigrate-v1.30.1-to-v1.29.1?expand=1"
    )


def test_pr_command_permission_failure_is_warning(
    repo_root: Path,
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    """PR creation can be blocked by repository settings without failing migration."""

    module = _load_migration_pr_module(repo_root)
    monkeypatch.setenv("GITHUB_REPOSITORY", "ThreeMonth03/example")

    module._run_pr_command(
        ["bash", "-lc", "exit 1"],
        checkout=tmp_path,
        bot_branch="automation/migrate-v1.30.1-to-v1.29.1",
        target_branch="sync/v1.29.1",
    )

    captured = capsys.readouterr()
    assert "WARNING: Could not create or update migration PR" in captured.err
    assert "https://github.com/ThreeMonth03/example/compare/" in captured.err


def test_pr_command_permission_failure_writes_github_summary(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Blocked PR creation should leave an actionable link in the Actions summary."""

    module = _load_migration_pr_module(repo_root)
    summary_path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_REPOSITORY", "ThreeMonth03/example")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))

    module._run_pr_command(
        ["bash", "-lc", "exit 1"],
        checkout=tmp_path,
        bot_branch="automation/migrate-v1.30.1-to-v1.29.1",
        target_branch="sync/v1.29.1",
    )

    summary = summary_path.read_text(encoding="utf-8")
    assert "Migration PR needs manual creation" in summary
    assert "sync/v1.29.1" in summary
    assert "automation/migrate-v1.30.1-to-v1.29.1" in summary
    assert "https://github.com/ThreeMonth03/example/compare/" in summary


def test_auto_merge_requires_enabled_exact_only_safe_report(repo_root: Path) -> None:
    """Auto-merge should only be requested for exact-only partial-safe migrations."""

    module = _load_migration_pr_module(repo_root)
    config = SimpleNamespace(
        migration=SimpleNamespace(
            auto_merge_when_clean=True,
            mode="exact-only",
            non_exact_policy="leave_empty_needs_translation",
        )
    )

    assert module.is_auto_merge_safe(
        config=config,
        report={"migrated_units": 4, "sentence_matches": 0},
    )
    assert module.is_auto_merge_safe(
        config=config,
        report={"migrated_units": 0, "updated_units": 4, "sentence_matches": 0},
    )
    assert not module.is_auto_merge_safe(
        config=config,
        report={"migrated_units": 0, "updated_units": 0, "sentence_matches": 0},
    )
    assert not module.is_auto_merge_safe(
        config=config,
        report={"migrated_units": 4, "sentence_matches": 1},
    )

    disabled_config = SimpleNamespace(
        migration=SimpleNamespace(
            auto_merge_when_clean=False,
            mode="exact-only",
            non_exact_policy="leave_empty_needs_translation",
        )
    )
    assert not module.is_auto_merge_safe(
        config=disabled_config,
        report={"migrated_units": 4, "sentence_matches": 0},
    )


def test_enable_auto_merge_requests_guarded_squash_merge(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Auto-merge requests should be pinned to the generated migration head SHA."""

    module = _load_migration_pr_module(repo_root)
    commands: list[list[str]] = []

    def fake_run(
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(module, "_run", fake_run)

    module.enable_auto_merge(
        checkout=tmp_path,
        pull_request_number="42",
        head_sha="abc123",
        bot_branch="automation/migrate-v1.30.1-to-v1.30.0",
        target_branch="sync/v1.30.0",
    )

    assert commands == [
        [
            "gh",
            "pr",
            "merge",
            "42",
            "--squash",
            "--auto",
            "--delete-branch",
            "--match-head-commit",
            "abc123",
        ]
    ]


def test_enable_auto_merge_falls_back_to_guarded_immediate_merge(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """If GitHub rejects auto-merge, safe synchronization PRs can merge directly."""

    module = _load_migration_pr_module(repo_root)
    commands: list[list[str]] = []

    def fake_run(
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(args)
        returncode = 1 if "--auto" in args else 0
        return subprocess.CompletedProcess(args=args, returncode=returncode)

    monkeypatch.setattr(module, "_run", fake_run)

    module.enable_auto_merge(
        checkout=tmp_path,
        pull_request_number="42",
        head_sha="abc123",
        bot_branch="automation/migrate-v1.30.1-to-v1.30.0",
        target_branch="sync/v1.30.0",
    )

    assert commands == [
        [
            "gh",
            "pr",
            "merge",
            "42",
            "--squash",
            "--auto",
            "--delete-branch",
            "--match-head-commit",
            "abc123",
        ],
        [
            "gh",
            "pr",
            "merge",
            "42",
            "--squash",
            "--delete-branch",
            "--match-head-commit",
            "abc123",
        ],
    ]


def _load_migration_pr_module(repo_root: Path) -> ModuleType:
    module_path = repo_root / "scripts" / "ci" / "create_translation_migration_prs.py"
    spec = importlib.util.spec_from_file_location("create_translation_migration_prs", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git_show(repo: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "show", revision],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_symbolic_ref(repo: Path) -> str | None:
    result = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _run_git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
