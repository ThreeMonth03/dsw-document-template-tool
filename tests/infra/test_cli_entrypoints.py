"""Smoke tests for repository CLI entrypoints."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import yaml


def _tool_cli(repo_root: Path, command: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one installed package console script from the repository virtualenv."""

    return subprocess.run(
        [str(repo_root / ".venv" / "bin" / command), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_render_regression_help(repo_root) -> None:
    """The main regression CLI should expose a working help screen."""

    result = _tool_cli(repo_root, "dsw-template-render-regression", "--help")
    assert result.returncode == 0
    assert "headless DSW template regression" in result.stdout
    assert "--config" in result.stdout


def test_render_project_help(repo_root) -> None:
    """The project render CLI should expose a working help screen."""

    result = _tool_cli(repo_root, "dsw-template-render-project", "--help")
    assert result.returncode == 0
    assert "existing or fixture DSW project" in result.stdout
    assert "--project-uuid" in result.stdout
    assert "--template-package" in result.stdout
    assert "--keep-created-project" in result.stdout


def test_transform_template_help(repo_root) -> None:
    """The transform CLI should expose its subcommands."""

    result = _tool_cli(repo_root, "dsw-template-transform", "--help")
    assert result.returncode == 0
    assert "Expand or compact DSW document templates" in result.stdout
    assert "expand" in result.stdout
    assert "compact" in result.stdout


def test_translation_tree_help(repo_root) -> None:
    """The translation-tree CLI should expose export/audit/sync commands."""

    result = _tool_cli(repo_root, "dsw-template-tree", "--help")
    assert result.returncode == 0
    assert "translator-facing trees" in result.stdout
    assert "export" in result.stdout
    assert "audit" in result.stdout
    assert "audit-output" in result.stdout
    assert "sync" in result.stdout
    assert "merge" in result.stdout

    result = _tool_cli(
        repo_root,
        "dsw-template-tree",
        "sync",
        "--help",
    )
    assert result.returncode == 0
    assert "--template-id" in result.stdout

    result = _tool_cli(
        repo_root,
        "dsw-template-tree",
        "audit",
        "--help",
    )
    assert result.returncode == 0
    assert "--tree" in result.stdout
    assert "--source" in result.stdout

    result = _tool_cli(
        repo_root,
        "dsw-template-tree",
        "audit-output",
        "--help",
    )
    assert result.returncode == 0
    assert "--source" in result.stdout
    assert "--output" in result.stdout

    result = _tool_cli(
        repo_root,
        "dsw-template-tree",
        "merge",
        "--help",
    )
    assert result.returncode == 0
    assert "--old-tree" in result.stdout
    assert "--new-tree" in result.stdout
    assert "--output" in result.stdout
    assert "--source-lang" in result.stdout
    assert "--target-lang" in result.stdout
    assert "--allow-sentence-matches" in result.stdout


def test_resolve_upstream_refs_expands_version_ranges(repo_root: Path, tmp_path: Path) -> None:
    """The CI helper should resolve semantic version ranges from an upstream remote."""

    remote = _build_upstream_template_remote(
        tmp_path,
        [
            ("v1.29.1", "1.29.1", "17.1"),
            ("v1.30.0", "1.30.0", "18.0"),
            ("v1.30.1", "1.30.1", "18.0"),
        ],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_upstream_refs.py"),
            "--remote",
            str(remote),
            "latest",
            "v1.30.0+",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    refs = result.stdout.strip().split()
    assert refs[0] == "latest"
    assert "v1.30.0" in refs
    assert "v1.30.1" in refs
    assert "v1.29.1" not in refs


def test_resolve_upstream_refs_rejects_empty_version_ranges(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Version ranges should fail loudly when upstream has no matching tags."""

    remote = _build_upstream_template_remote(
        tmp_path,
        [
            ("v1.29.1", "1.29.1", "17.1"),
            ("v1.30.1", "1.30.1", "18.0"),
        ],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_upstream_refs.py"),
            "--remote",
            str(remote),
            "v9.99.0+",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "did not match any upstream tags" in result.stderr


def test_resolve_upstream_refs_normalizes_github_owner_repo() -> None:
    """GitHub owner/repo shorthand should be accepted by the resolver."""

    from scripts.ci.resolve_upstream_refs import normalize_git_remote

    assert (
        normalize_git_remote("ds-wizard/science-europe-template")
        == "https://github.com/ds-wizard/science-europe-template.git"
    )
    assert (
        normalize_git_remote("https://github.com/ds-wizard/science-europe-template.git")
        == "https://github.com/ds-wizard/science-europe-template.git"
    )


def test_discover_dsw_compat_reports_supported_refs(repo_root: Path, tmp_path: Path) -> None:
    """The compatibility discovery helper should accept known metamodel mappings."""

    remote = _build_upstream_template_remote(
        tmp_path,
        [
            ("v1.29.1", "1.29.1", "17.1"),
            ("v1.30.0", "1.30.0", "18.0"),
        ],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "discover_dsw_compat.py"),
            "--remote",
            str(remote),
            "--cache",
            str(tmp_path / "cache-supported"),
            "v1.29.1+",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "DSW Compatibility Discovery" in result.stdout
    assert "`v1.29.1` | `v1.29.1` | `17.1`" in result.stdout
    assert "`v1.30.0` | `v1.30.0` | `18.0`" in result.stdout
    assert "covered" in result.stdout


def test_discover_dsw_compat_uses_env_report_paths(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The discovery helper should keep Makefile report handling thin."""

    remote = _build_upstream_template_remote(
        tmp_path,
        [("v1.30.0", "1.30.0", "18.0")],
    )
    summary = tmp_path / "summary.md"
    report = tmp_path / "report.md"
    env = os.environ.copy()
    env["GITHUB_STEP_SUMMARY"] = str(summary)
    env["UPSTREAM_TEMPLATE_DISCOVERY_REPORT"] = str(report)

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "discover_dsw_compat.py"),
            "--remote",
            str(remote),
            "--cache",
            str(tmp_path / "cache-env-report"),
            "v1.30.0",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "DSW Compatibility Discovery" in summary.read_text(encoding="utf-8")
    assert "`v1.30.0`" in report.read_text(encoding="utf-8")


def test_discover_dsw_compat_normalizes_remote_for_all_git_steps(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """GitHub owner/repo shorthand should be normalized before all git operations."""

    module = _load_script_module(
        repo_root / "scripts" / "ci" / "discover_dsw_compat.py",
        "discover_dsw_compat_test",
    )
    seen: dict[str, str] = {}

    monkeypatch.setattr(module, "load_preview_runtimes", lambda _: ())

    def fake_resolve_refs(*, remote: str, refs: list[str]) -> list[str]:
        seen["resolve"] = remote
        assert refs == ["v1.30.0"]
        return []

    def fake_prepare_cache(cache: Path, remote: str) -> None:
        seen["prepare"] = remote
        assert cache == tmp_path / "cache"

    monkeypatch.setattr(module, "resolve_refs", fake_resolve_refs)
    monkeypatch.setattr(module, "prepare_cache", fake_prepare_cache)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "discover_dsw_compat.py",
            "--remote",
            "ds-wizard/science-europe-template",
            "--cache",
            str(tmp_path / "cache"),
            "v1.30.0",
        ],
    )

    module.main()

    capsys.readouterr()
    expected_remote = "https://github.com/ds-wizard/science-europe-template.git"
    assert seen == {"resolve": expected_remote, "prepare": expected_remote}


def test_discover_dsw_compat_fails_unknown_metamodel(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Unknown upstream metamodels should fail clearly instead of being skipped."""

    remote = _build_upstream_template_remote(
        tmp_path,
        [
            ("v1.30.0", "1.30.0", "18.0"),
            ("v1.31.0", "1.31.0", "19.0"),
        ],
    )
    summary = tmp_path / "summary.md"
    report = tmp_path / "compat-report.md"
    metamodel_source = tmp_path / "metamodel-source.html"
    metamodel_source.write_text(
        "<h3>Version 19.0 (since 4.35.0)</h3>\n<h3>Version 18.0 (since 4.29.0)</h3>\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "discover_dsw_compat.py"),
            "--remote",
            str(remote),
            "--cache",
            str(tmp_path / "cache-unsupported"),
            "--summary",
            str(summary),
            "--report",
            str(report),
            "--metamodel-source-url",
            metamodel_source.as_uri(),
            "v1.30.0+",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Unsupported Metamodels" in result.stdout
    assert "metamodelVersion=19.0" in result.stdout
    assert "DSW 4.35.0" in result.stdout
    assert metamodel_source.as_uri() in result.stdout
    assert summary.is_file()
    assert "v1.31.0" in summary.read_text(encoding="utf-8")
    assert report.is_file()
    assert "Unsupported Metamodels" in report.read_text(encoding="utf-8")


def test_create_dsw_compat_pr_helper_dry_run(repo_root: Path, tmp_path: Path) -> None:
    """The compatibility PR helper should render a reviewable probe file."""

    report = tmp_path / "discovery.md"
    output = tmp_path / "dsw-compatibility-probe.md"
    report.write_text(
        "## DSW Compatibility Discovery\n\n"
        "| Ref | Version | metamodelVersion | Runtime | Status |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `v1.30.0` | `v1.30.0` | `18.0` | 18-0 / DSW 4.30 / TDK 4.30.2 | covered |\n"
        "| `v1.30.1` | `v1.30.1` | `18.0` | 18-0 / DSW 4.30 / TDK 4.30.2 | covered |\n"
        "| `v1.31.0` | `v1.31.0` | `19.0` | - | unsupported |\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py"),
            "--report",
            str(report),
            "--report-path",
            str(output),
            "--repository",
            "owner/repo",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    rendered = output.read_text(encoding="utf-8")
    assert "DSW Metamodel Compatibility Probe" in rendered
    assert "v1.31.0" in rendered
    assert "reuses metamodel `18.0` runtime" in rendered
    assert "Maintainer Checklist" in rendered


def test_create_dsw_compat_pr_defaults_to_metamodel_specific_branch(repo_root: Path) -> None:
    """The workflow path should use a stable branch name without passing --branch."""

    module = _load_script_module(
        repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py",
        "create_dsw_compat_pr_defaults_test",
    )
    plan = module.ProbePlan(
        runtimes=(),
        changes=(
            module.ProbeChange(
                metamodel_version="19.0",
                min_version="v1.31.0",
                previous_metamodel_version="18.0",
                previous_dsw_version="4.30",
                previous_tdk_version="4.30.2",
            ),
        ),
    )

    assert module.default_branch_for_plan(plan) == "automation/dsw-compat-probe-19-0"
    assert (
        module.default_title_for_plan(plan)
        == "Probe DSW document-template metamodel 19.0 compatibility"
    )


def test_create_dsw_compat_pr_can_probe_multiple_new_metamodels(repo_root: Path) -> None:
    """A long gap with multiple new metamodels should still generate probe rows."""

    module = _load_script_module(
        repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py",
        "create_dsw_compat_pr_test",
    )
    report = (
        "## DSW Compatibility Discovery\n\n"
        "| Ref | Version | metamodelVersion | Runtime | Status |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `v1.30.1` | `v1.30.1` | `18.0` | 18-0 / DSW 4.30 / TDK 4.30.2 | covered |\n"
        "| `v1.31.0` | `v1.31.0` | `19.0` | - | unsupported |\n"
        "| `v1.32.0` | `v1.32.0` | `20.0` | - | unsupported |\n"
    )
    compat = """
schema_version: 1
runtimes:
  - metamodel_key: "18-0"
    metamodel_version: "18.0"
    dsw_version: "4.30"
    tdk_version: "4.30.2"
    min_version: "v1.30.0"
    max_version: null
    upstream_template_artifact_refs: "v1.30.0+"
    run_preview_regression: true
    strict_project_preview: true
"""

    plan = module.build_probe_plan(report=report, compat_text=compat)
    rendered_config = module.render_compat_config(plan.runtimes)

    assert len(plan.changes) == 2
    assert 'metamodel_version: "19.0"' in rendered_config
    assert 'min_version: "v1.31.0"' in rendered_config
    assert 'max_version: "v1.31.0"' in rendered_config
    assert 'metamodel_version: "20.0"' in rendered_config
    assert 'min_version: "v1.32.0"' in rendered_config


def test_create_dsw_compat_pr_starts_new_branch_from_remote_base(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The compatibility PR branch should not inherit a non-base checkout HEAD."""

    origin = tmp_path / "origin.git"
    worktree = tmp_path / "worktree"
    report = tmp_path / "discovery.md"

    _init_git_worktree_with_origin(worktree=worktree, origin=origin)
    base_commit = _git_output(worktree, "rev-parse", "master")

    _git(worktree, "checkout", "-b", "feature")
    (worktree / "feature.txt").write_text(
        "must not leak into automation branch\n",
        encoding="utf-8",
    )
    _git(worktree, "add", "feature.txt")
    _git(worktree, "commit", "-m", "feature")
    feature_commit = _git_output(worktree, "rev-parse", "feature")
    subprocess.run(
        ["git", "-C", str(worktree), "update-ref", "-d", "refs/remotes/origin/master"],
        check=False,
    )

    _write_dsw_compat_discovery_report(report)
    env = _fake_gh_env(tmp_path / "bin")
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py"),
            "--report",
            str(report),
            "--report-path",
            "docs/compatibility/dsw-compatibility-probe.md",
            "--repository",
            "owner/repo",
            "--base",
            "master",
            "--branch",
            "automation/dsw-compat-probe-19-0",
        ],
        cwd=worktree,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    automation_parent = _git_output(worktree, "rev-parse", "HEAD^")
    tree_files = _git_output(
        worktree,
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
    )
    assert automation_parent == base_commit
    assert automation_parent != feature_commit
    assert "feature.txt" not in tree_files
    assert _git_show_bare(
        origin,
        "automation/dsw-compat-probe-19-0:docs/compatibility/dsw-compatibility-probe.md",
    )
    updated_config = _git_show_bare(
        origin,
        "automation/dsw-compat-probe-19-0:config/dsw-compat.yml",
    )
    assert 'metamodel_version: "19.0"' in updated_config
    assert 'dsw_version: "4.30"' in updated_config
    assert 'tdk_version: "4.30.2"' in updated_config
    assert 'max_version: "v1.30.1"' in updated_config
    assert 'upstream_template_artifact_refs: "v1.30.0 v1.30.1"' in updated_config


def test_create_dsw_compat_pr_updates_branch_open_in_another_worktree(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The probe PR helper should not depend on checking out its local branch."""

    origin = tmp_path / "origin.git"
    worktree = tmp_path / "worktree"
    open_worktree = tmp_path / "open-automation-branch"
    report = tmp_path / "discovery.md"

    _init_git_worktree_with_origin(worktree=worktree, origin=origin)
    _git(worktree, "checkout", "-b", "automation/dsw-compat-probe-19-0")
    compatibility_report = worktree / "docs" / "compatibility" / "dsw-compatibility-probe.md"
    compatibility_report.parent.mkdir(parents=True)
    compatibility_report.write_text("old compatibility report\n", encoding="utf-8")
    _git(worktree, "add", "docs/compatibility/dsw-compatibility-probe.md")
    _git(worktree, "commit", "-m", "docs: old compatibility report")
    _git(worktree, "push", "-u", "origin", "automation/dsw-compat-probe-19-0")
    _git(worktree, "checkout", "master")
    _git(worktree, "worktree", "add", str(open_worktree), "automation/dsw-compat-probe-19-0")

    _write_dsw_compat_discovery_report(report)
    env = _fake_gh_env(tmp_path / "bin")
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py"),
                "--report",
                str(report),
                "--report-path",
                "docs/compatibility/dsw-compatibility-probe.md",
                "--repository",
                "owner/repo",
                "--base",
                "master",
                "--branch",
                "automation/dsw-compat-probe-19-0",
            ],
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        _git(worktree, "worktree", "remove", "--force", str(open_worktree))

    assert result.returncode == 0, result.stdout + result.stderr
    updated_report = _git_show_bare(
        origin,
        "automation/dsw-compat-probe-19-0:docs/compatibility/dsw-compatibility-probe.md",
    )
    assert "DSW Metamodel Compatibility Probe" in updated_report
    assert "old compatibility report" not in updated_report


def test_create_dsw_compat_pr_reopens_pr_when_existing_branch_is_unchanged(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """An unchanged automation branch should still ensure an open PR exists."""

    origin = tmp_path / "origin.git"
    worktree = tmp_path / "worktree"
    gh_log = tmp_path / "gh.log"
    report = tmp_path / "discovery.md"

    _init_git_worktree_with_origin(worktree=worktree, origin=origin)
    _write_dsw_compat_discovery_report(report)
    env = _fake_gh_env(tmp_path / "bin-first")
    first_result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py"),
            "--report",
            str(report),
            "--repository",
            "owner/repo",
            "--base",
            "master",
            "--branch",
            "automation/dsw-compat-probe-19-0",
        ],
        cwd=worktree,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    existing_branch_commit = _git_output(
        worktree,
        "rev-parse",
        "origin/automation/dsw-compat-probe-19-0",
    )

    _git(worktree, "checkout", "master")
    env = _fake_gh_env(tmp_path / "bin-second", log_path=gh_log)
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py"),
            "--report",
            str(report),
            "--repository",
            "owner/repo",
            "--base",
            "master",
            "--branch",
            "automation/dsw-compat-probe-19-0",
        ],
        cwd=worktree,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ensuring PR exists" in result.stdout
    assert (
        _git_output(worktree, "rev-parse", "origin/automation/dsw-compat-probe-19-0")
        == existing_branch_commit
    )
    assert "pr view automation/dsw-compat-probe-19-0" in gh_log.read_text(encoding="utf-8")
    assert "pr create" in gh_log.read_text(encoding="utf-8")


def test_create_translation_migration_prs_help(repo_root: Path) -> None:
    """The migration PR helper should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_translation_migration_prs.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "cross-version translation migration PRs" in result.stdout
    assert "--source-version" in result.stdout
    assert "--target-version" in result.stdout
    assert "--create-pr" in result.stdout
    assert "--clean-artifact-root" in result.stdout


def test_create_dsw_compat_pr_help(repo_root: Path) -> None:
    """The DSW compatibility probe PR helper should expose a help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "DSW compatibility probe" in result.stdout
    assert "--report" in result.stdout
    assert "--compat" in result.stdout
    assert "--dry-run" in result.stdout


def test_sync_translation_version_branches_help(repo_root: Path) -> None:
    """The version-branch sync helper should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "sync_translation_version_branches.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "translation version branches" in result.stdout
    assert "--clean-artifact-root" in result.stdout
    assert "--github-output" in result.stdout


def test_validate_translation_config_help(repo_root: Path) -> None:
    """The translation config validator should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "validate_translation_config.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "translation configuration" in result.stdout
    assert "--config" in result.stdout
    assert "--summary" in result.stdout


def test_download_clean_scaffold_artifacts_help(repo_root: Path) -> None:
    """The clean scaffold downloader should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "download_clean_scaffold_artifacts.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "clean scaffold artifacts" in result.stdout
    assert "--run-id" in result.stdout
    assert "--repo" in result.stdout
    assert "--workflow" in result.stdout
    assert "--artifact" in result.stdout


def test_resolve_migration_source_help(repo_root: Path) -> None:
    """The migration source resolver should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_migration_source.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "source version" in result.stdout
    assert "--event-name" in result.stdout
    assert "--github-output" in result.stdout


def test_write_preview_status_records_ci_metadata(repo_root: Path, tmp_path: Path) -> None:
    """The scaffold-preview status helper should create machine-readable artifacts."""

    output_path = tmp_path / "failed.json"
    env = os.environ.copy()
    env["DSW_VERSION"] = "4.26"
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "write_preview_status.py"),
            "--output",
            str(output_path),
            "--status",
            "failed",
            "--reason",
            "render_failed",
            "--template-version",
            "v1.29.1",
            "--template-metamodel-version",
            "17.1",
            "--preview-metamodel-version",
            "17.1",
            "--exit-code",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "status": "failed",
        "reason": "render_failed",
        "template_metamodel_version": "17.1",
        "preview_metamodel_version": "17.1",
        "template_version": "v1.29.1",
        "exit_code": 2,
        "dsw_version": "4.26",
    }


def test_stage_release_assets_help(repo_root: Path) -> None:
    """The release asset staging helper should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "stage_release_assets.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "GitHub Release assets" in result.stdout
    assert "--asset" in result.stdout
    assert "--archive-dir" in result.stdout


def test_upstream_template_artifacts_help(repo_root: Path) -> None:
    """The upstream artifact helper should own the heavy Makefile workflow logic."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "upstream_template_artifacts.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "clean upstream Science Europe scaffold artifacts" in result.stdout
    assert "build-artifacts" in result.stdout
    assert "render-previews" in result.stdout


def test_generate_regression_config_help(repo_root: Path) -> None:
    """The regression config generator should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "generate_regression_config.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "version-aware regression config" in result.stdout
    assert "--workspace-root" in result.stdout
    assert "--version" in result.stdout


def test_generate_compat_ledger_help(repo_root: Path) -> None:
    """The compatibility ledger generator should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "generate_compat_ledger.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "compatibility ledgers" in result.stdout
    assert "--workspace-root" in result.stdout
    assert "--output-dir" in result.stdout


def test_run_regression_plan_help(repo_root: Path) -> None:
    """The regression-plan runner should expose a working help screen."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "run_regression_plan.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "versions recommended by a compatibility plan" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--metamodel-version" in result.stdout
    assert "--plan" in result.stdout


def test_generate_regression_config_selects_latest_matching_workspace(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """CI regression should target the newest built workspace for the matrix."""

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    base_config = config_dir / "regression.ci.yml"
    base_config.write_text(
        """
api:
  url: ${DSW_API_URL}
  email: ${DSW_EMAIL}
  password: ${DSW_PASSWORD}
subjects:
  baseline:
    kind: local_dir
    value: old-baseline
  candidate:
    kind: local_dir
    value: old-candidate
regression:
  mode: preview
  format_uuid: html-format-uuid
  output_dir: ../outputs/preview
fixtures:
  - name: empty
    project_uuid: 11111111-1111-4111-8111-111111111111
""".strip()
        + "\n",
        encoding="utf-8",
    )

    workspace_root = tmp_path / "outputs" / "upstream-workspaces" / "dsw-science-europe"
    _write_regression_workspace(workspace_root, "dsw-science-europe", "1.29.1", "17.1")
    _write_regression_workspace(workspace_root, "dsw-science-europe", "1.30.0", "18.0")
    _write_regression_workspace(workspace_root, "dsw-science-europe", "1.30.1", "18.0")
    generated_config = config_dir / ".generated-regression.ci.yml"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "generate_regression_config.py"),
            "--base-config",
            str(base_config),
            "--output",
            str(generated_config),
            "--workspace-root",
            str(workspace_root),
            "--source-template-id",
            "dsw-science-europe",
            "--metamodel-version",
            "18.0",
            "--version",
            "latest",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "v1.30.1" in result.stdout
    payload = yaml.safe_load(generated_config.read_text(encoding="utf-8"))
    assert (
        payload["subjects"]["baseline"]["value"]
        == "../outputs/upstream-workspaces/dsw-science-europe/v1.30.1/compact/"
        "dsw-science-europe-1.30.1"
    )
    assert (
        payload["subjects"]["candidate"]["value"]
        == "../outputs/upstream-workspaces/dsw-science-europe/v1.30.1/"
        "expanded-regression/dsw-science-europe-1.30.1"
    )
    assert payload["subjects"]["baseline"]["stage_id"] == "ci:science-europe-compact:1.30.1"
    assert payload["subjects"]["candidate"]["stage_id"] == "ci:science-europe-expanded:1.30.1"


def test_generate_regression_config_can_version_output_dir(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Multi-version regression runs should not overwrite preview artifacts."""

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    base_config = config_dir / "regression.ci.yml"
    base_config.write_text(
        """
subjects:
  baseline:
    kind: local_dir
    value: old-baseline
  candidate:
    kind: local_dir
    value: old-candidate
regression:
  output_dir: ../outputs/preview
generated_fixtures:
  - name_prefix: random-project
    count: 80
""".strip()
        + "\n",
        encoding="utf-8",
    )
    workspace_root = tmp_path / "outputs" / "upstream-workspaces" / "dsw-science-europe"
    _write_regression_workspace(workspace_root, "dsw-science-europe", "1.30.1", "18.0")
    generated_config = config_dir / ".generated-regression.ci.v1.30.1.yml"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "generate_regression_config.py"),
            "--base-config",
            str(base_config),
            "--output",
            str(generated_config),
            "--workspace-root",
            str(workspace_root),
            "--source-template-id",
            "dsw-science-europe",
            "--metamodel-version",
            "18.0",
            "--version",
            "v1.30.1",
            "--output-dir-suffix",
            "v1.30.1",
            "--generated-fixture-count",
            "20",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = yaml.safe_load(generated_config.read_text(encoding="utf-8"))
    assert payload["regression"]["output_dir"] == "../outputs/preview/v1.30.1"
    assert payload["generated_fixtures"][0]["count"] == 20


def test_run_regression_plan_selects_recommended_versions_for_metamodel(
    repo_root: Path,
) -> None:
    """The plan runner should only select recommended versions for its runtime."""

    module = _load_script_module(
        repo_root / "scripts" / "ci" / "run_regression_plan.py",
        "run_regression_plan_test",
    )
    plan = {
        "candidates": [
            {
                "version": "v1.29.1",
                "metamodel_version": "17.1",
                "recommended": True,
                "reasons": ["first_for_metamodel"],
            },
            {
                "version": "v1.30.0",
                "metamodel_version": "18.0",
                "recommended": True,
                "reasons": ["first_for_metamodel"],
            },
            {
                "version": "v1.30.1",
                "metamodel_version": "18.0",
                "recommended": False,
                "reasons": [],
            },
        ]
    }

    selected = module.select_planned_regressions(
        plan=plan,
        metamodel_version="18.0",
        fallback_version="latest",
    )

    assert [item.version for item in selected] == ["v1.30.0"]
    assert selected[0].reasons == ("first_for_metamodel",)
    assert selected[0].profile == "smoke"


def test_run_regression_plan_uses_full_profile_for_latest_or_changed_versions(
    repo_root: Path,
) -> None:
    """Only high-value changed/latest candidates should run the full fixture set."""

    module = _load_script_module(
        repo_root / "scripts" / "ci" / "run_regression_plan.py",
        "run_regression_plan_profile_test",
    )

    assert (
        module.PlannedRegression(
            version="v1.30.0",
            metamodel_version="18.0",
            reasons=("first_for_metamodel",),
        ).profile
        == "smoke"
    )
    assert (
        module.PlannedRegression(
            version="v1.30.1",
            metamodel_version="18.0",
            reasons=("latest_for_metamodel",),
        ).profile
        == "full"
    )
    assert (
        module.PlannedRegression(
            version="v1.30.1",
            metamodel_version="18.0",
            reasons=("structure_signature_changed",),
        ).profile
        == "full"
    )


def test_run_regression_plan_dry_run_writes_versioned_configs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Dry-run mode should validate the plan without requiring a DSW server."""

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    base_config = config_dir / "regression.ci.yml"
    base_config.write_text(
        """
subjects:
  baseline:
    kind: local_dir
    value: old-baseline
  candidate:
    kind: local_dir
    value: old-candidate
regression:
  output_dir: ../outputs/preview
generated_fixtures:
  - name_prefix: random-project
    count: 80
""".strip()
        + "\n",
        encoding="utf-8",
    )
    workspace_root = tmp_path / "outputs" / "upstream-workspaces" / "dsw-science-europe"
    _write_regression_workspace(workspace_root, "dsw-science-europe", "1.30.0", "18.0")
    _write_regression_workspace(workspace_root, "dsw-science-europe", "1.30.1", "18.0")
    plan_path = tmp_path / "regression-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "version": "v1.30.0",
                        "metamodel_version": "18.0",
                        "recommended": True,
                        "reasons": ["first_for_metamodel"],
                    },
                    {
                        "version": "v1.30.1",
                        "metamodel_version": "18.0",
                        "recommended": True,
                        "reasons": ["latest_for_metamodel"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "run_regression_plan.py"),
            "--base-config",
            str(base_config),
            "--dry-run",
            "--generated-config-dir",
            str(config_dir),
            "--metamodel-version",
            "18.0",
            "--plan",
            str(plan_path),
            "--source-template-id",
            "dsw-science-europe",
            "--workspace-root",
            str(workspace_root),
            "--smoke-generated-fixture-count",
            "7",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    first_config = yaml.safe_load(
        (config_dir / ".generated-regression.ci.18-0.v1.30.0.smoke.yml").read_text(encoding="utf-8")
    )
    latest_config = yaml.safe_load(
        (config_dir / ".generated-regression.ci.18-0.v1.30.1.full.yml").read_text(encoding="utf-8")
    )
    assert first_config["regression"]["output_dir"] == "../outputs/preview/v1.30.0-smoke"
    assert first_config["generated_fixtures"][0]["count"] == 7
    assert latest_config["regression"]["output_dir"] == "../outputs/preview/v1.30.1"
    assert latest_config["generated_fixtures"][0]["count"] == 80
    assert "Dry run" in result.stdout
    assert "Running smoke regression for v1.30.0" in result.stdout
    assert "Running full regression for v1.30.1" in result.stdout


def test_upstream_template_artifacts_lists_and_fetches_local_tags(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The upstream helper should replace Makefile shell fetch/list logic."""

    remote = _build_upstream_template_remote(
        tmp_path,
        [
            ("v1.29.1", "1.29.1", "17.1"),
            ("v1.30.1", "1.30.1", "18.0"),
        ],
    )

    list_result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "upstream_template_artifacts.py"),
            "list-tags",
            "--remote",
            str(remote),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert list_result.returncode == 0, list_result.stdout + list_result.stderr
    assert list_result.stdout.strip().splitlines() == ["v1.29.1", "v1.30.1"]

    cache = tmp_path / "cache"
    fetch_result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "upstream_template_artifacts.py"),
            "fetch",
            "--remote",
            str(remote),
            "--ref",
            "latest",
            "--cache",
            str(cache),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert fetch_result.returncode == 0, fetch_result.stdout + fetch_result.stderr
    assert "resolved to v1.30.1" in fetch_result.stdout
    assert json.loads((cache / "template.json").read_text(encoding="utf-8"))["version"] == "1.30.1"


def test_upstream_template_artifacts_normalizes_remote_for_subcommands(
    repo_root: Path,
    monkeypatch,
    capsys,
) -> None:
    """Owner/repo shorthand should be normalized before upstream git operations."""

    module = _load_script_module(
        repo_root / "scripts" / "ci" / "upstream_template_artifacts.py",
        "upstream_template_artifacts_test",
    )
    seen: dict[str, str] = {}

    def fake_list_upstream_tags(remote: str) -> None:
        seen["remote"] = remote

    monkeypatch.setattr(module, "list_upstream_tags", fake_list_upstream_tags)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "upstream_template_artifacts.py",
            "list-tags",
            "--remote",
            "ds-wizard/science-europe-template",
        ],
    )

    module.main()

    capsys.readouterr()
    assert seen["remote"] == "https://github.com/ds-wizard/science-europe-template.git"


def test_resolve_upstream_refs_expands_artifact_ranges(repo_root: Path, tmp_path: Path) -> None:
    """The clean scaffold artifact range should include all supported tags."""

    remote = _build_upstream_template_remote(
        tmp_path,
        [
            ("v1.29.0", "1.29.0", "17.0"),
            ("v1.29.1", "1.29.1", "17.1"),
            ("v1.30.1", "1.30.1", "18.0"),
        ],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_upstream_refs.py"),
            "--remote",
            str(remote),
            "v1.29.1+",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    refs = result.stdout.strip().split()
    assert refs[0] == "v1.29.1"
    assert "v1.30.1" in refs
    assert "v1.29.0" not in refs


def test_makefile_defaults_are_dictionary_sorted(repo_root: Path) -> None:
    """User-overridable Makefile defaults should stay easy to scan."""

    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    variables = [
        line.split("?", 1)[0].strip()
        for line in makefile.splitlines()
        if "?=" in line and not line.startswith("\t")
    ]

    assert variables == sorted(variables)
    assert "UPSTREAM_TEMPLATE_MIN_SUPPORTED_REF" not in variables
    assert "UPSTREAM_TEMPLATE_ARTIFACT_MIN_REF" in variables
    assert "UPSTREAM_TEMPLATE_TEST_MIN_REF" in variables


def test_makefile_phony_targets_are_dictionary_sorted(repo_root: Path) -> None:
    """The Makefile target registry should avoid hand-ordered drift."""

    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    phony_line = next(line for line in makefile.splitlines() if line.startswith(".PHONY:"))
    targets = phony_line.split(":", 1)[1].split()

    assert targets == sorted(targets)


def test_makefile_keeps_upstream_workflows_in_python_helpers(repo_root: Path) -> None:
    """Makefile should stay a thin command router, not a shell workflow script."""

    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")

    assert "scripts/ci/upstream_template_artifacts.py" in makefile
    assert "for ref in $$refs" not in makefile
    assert "report_args" not in makefile
    assert "summary_args" not in makefile
    assert "shopt -s nullglob" not in makefile
    assert "python3 -c 'import json" not in makefile


def test_dsw_tdk_verify_command_is_available() -> None:
    """The dsw-tdk verify command should be installed for Makefile targets."""

    executable = Path(sys.executable).with_name("dsw-tdk")
    result = subprocess.run(
        [str(executable), "verify", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Usage: dsw-tdk verify" in result.stdout


def _init_git_worktree_with_origin(*, worktree: Path, origin: Path) -> None:
    _git(origin.parent, "init", "--bare", "--initial-branch=master", str(origin))
    worktree.mkdir()
    _git(worktree, "init", "--initial-branch=master")
    _git(worktree, "config", "user.name", "Test Bot")
    _git(worktree, "config", "user.email", "test@example.com")
    (worktree / "README.md").write_text("base\n", encoding="utf-8")
    config_dir = worktree / "config"
    config_dir.mkdir()
    (config_dir / "dsw-compat.yml").write_text(
        """
schema_version: 1
runtimes:
  - metamodel_key: "17-1"
    metamodel_version: "17.1"
    dsw_version: "4.26"
    tdk_version: "4.26.1"
    min_version: "v1.29.1"
    max_version: "v1.29.1"
    upstream_template_artifact_refs: "v1.29.1"
    run_preview_regression: false
    strict_project_preview: true
  - metamodel_key: "18-0"
    metamodel_version: "18.0"
    dsw_version: "4.30"
    tdk_version: "4.30.2"
    min_version: "v1.30.0"
    max_version: "v1.30.0"
    upstream_template_artifact_refs: "v1.30.0+"
    run_preview_regression: true
    strict_project_preview: true
""".lstrip(),
        encoding="utf-8",
    )
    _git(worktree, "add", "README.md")
    _git(worktree, "add", "config/dsw-compat.yml")
    _git(worktree, "commit", "-m", "base")
    _git(worktree, "remote", "add", "origin", str(origin))
    _git(worktree, "push", "-u", "origin", "master")


def _write_dsw_compat_discovery_report(path: Path) -> None:
    path.write_text(
        "## DSW Compatibility Discovery\n\n"
        "| Ref | Version | metamodelVersion | Runtime | Status |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `v1.30.0` | `v1.30.0` | `18.0` | 18-0 / DSW 4.30 / TDK 4.30.2 | covered |\n"
        "| `v1.30.1` | `v1.30.1` | `18.0` | 18-0 / DSW 4.30 / TDK 4.30.2 | covered |\n"
        "| `v1.31.0` | `v1.31.0` | `19.0` | - | unsupported |\n",
        encoding="utf-8",
    )


def _load_script_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_gh_env(bin_dir: Path, *, log_path: Path | None = None) -> dict[str, str]:
    bin_dir.mkdir()
    fake_gh = bin_dir / "gh"
    log_line = f'printf "%s\\n" "$*" >> "{log_path}"\n' if log_path else ""
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        f"{log_line}"
        'if [ "$1" = "pr" ] && [ "$2" = "view" ]; then\n'
        "  exit 1\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    return env


def _build_upstream_template_remote(
    tmp_path: Path,
    versions: list[tuple[str, str, str]],
) -> Path:
    """Create a tiny git repo with tagged template.json versions."""

    remote = tmp_path / "upstream-template"
    remote.mkdir()
    _git(remote, "init", "--initial-branch=main")
    _git(remote, "config", "user.name", "Test Bot")
    _git(remote, "config", "user.email", "test@example.com")
    for tag, version, metamodel_version in versions:
        (remote / "template.json").write_text(
            json.dumps(
                {
                    "id": "science-europe",
                    "version": version,
                    "metamodelVersion": metamodel_version,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        _git(remote, "add", "template.json")
        _git(remote, "commit", "-m", f"template {version}")
        _git(remote, "tag", tag)
    return remote


def _write_regression_workspace(
    workspace_root: Path,
    source_template_id: str,
    version: str,
    metamodel_version: str,
) -> None:
    template_name = f"{source_template_id}-{version}"
    for stage in ("compact", "expanded-regression"):
        template_dir = workspace_root / f"v{version}" / stage / template_name
        template_dir.mkdir(parents=True)
        (template_dir / "template.json").write_text(
            json.dumps(
                {
                    "organizationId": "dsw",
                    "templateId": "science-europe",
                    "version": version,
                    "metamodelVersion": metamodel_version,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def _git_show_bare(repo: Path, revision: str) -> str:
    return subprocess.run(
        ["git", "--git-dir", str(repo), "show", revision],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout
