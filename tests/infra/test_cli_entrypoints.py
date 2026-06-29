"""Smoke tests for repository CLI entrypoints."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_render_regression_help(repo_root) -> None:
    """The main regression CLI should expose a working help screen."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "render_regression.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "headless DSW template regression" in result.stdout
    assert "--config" in result.stdout


def test_render_project_help(repo_root) -> None:
    """The project render CLI should expose a working help screen."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "render_project.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "existing or fixture DSW project" in result.stdout
    assert "--project-uuid" in result.stdout
    assert "--keep-created-project" in result.stdout


def test_transform_template_help(repo_root) -> None:
    """The transform CLI should expose its subcommands."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "transform_template.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Expand or compact DSW document templates" in result.stdout
    assert "expand" in result.stdout
    assert "compact" in result.stdout


def test_translation_tree_help(repo_root) -> None:
    """The translation-tree CLI should expose export/audit/sync commands."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "translation_tree.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "translator-facing trees" in result.stdout
    assert "export" in result.stdout
    assert "audit" in result.stdout
    assert "audit-output" in result.stdout
    assert "sync" in result.stdout
    assert "merge" in result.stdout

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "translation_tree.py"), "sync", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--template-id" in result.stdout

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "translation_tree.py"), "audit", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--tree" in result.stdout
    assert "--source" in result.stdout

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "src" / "translation_tree.py"),
            "audit-output",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--source" in result.stdout
    assert "--output" in result.stdout

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "src" / "translation_tree.py"),
            "merge",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--old-tree" in result.stdout
    assert "--new-tree" in result.stdout
    assert "--output" in result.stdout
    assert "--source-lang" in result.stdout
    assert "--target-lang" in result.stdout
    assert "--allow-sentence-matches" in result.stdout


def test_resolve_upstream_refs_expands_version_ranges(repo_root: Path) -> None:
    """The CI helper should resolve semantic version ranges from an upstream remote."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_upstream_refs.py"),
            "--remote",
            "https://github.com/ds-wizard/science-europe-template.git",
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
    """The compatibility PR helper should render a reviewable investigation file."""

    report = tmp_path / "discovery.md"
    output = tmp_path / "unsupported-metamodels.md"
    report.write_text(
        "## DSW Compatibility Discovery\n\n"
        "| Ref | Version | metamodelVersion | Runtime | Status |\n"
        "| --- | --- | --- | --- | --- |\n"
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
    assert "Unsupported DSW Metamodel Compatibility" in rendered
    assert "v1.31.0" in rendered
    assert "Maintainer Checklist" in rendered


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
            "docs/compatibility/unsupported-metamodels.md",
            "--repository",
            "owner/repo",
            "--base",
            "master",
            "--branch",
            "automation/dsw-compat-review",
        ],
        cwd=worktree,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    automation_parent = _git_output(worktree, "rev-parse", "automation/dsw-compat-review^")
    tree_files = _git_output(
        worktree,
        "ls-tree",
        "-r",
        "--name-only",
        "automation/dsw-compat-review",
    )
    assert automation_parent == base_commit
    assert automation_parent != feature_commit
    assert "feature.txt" not in tree_files


def test_create_dsw_compat_pr_reopens_pr_when_existing_branch_is_unchanged(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """An unchanged automation branch should still ensure an open PR exists."""

    origin = tmp_path / "origin.git"
    worktree = tmp_path / "worktree"
    gh_log = tmp_path / "gh.log"
    report = tmp_path / "discovery.md"
    rendered_report = tmp_path / "rendered-report.md"

    _init_git_worktree_with_origin(worktree=worktree, origin=origin)
    _write_dsw_compat_discovery_report(report)
    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_dsw_compat_pr.py"),
            "--report",
            str(report),
            "--report-path",
            str(rendered_report),
            "--repository",
            "owner/repo",
            "--dry-run",
        ],
        check=True,
    )

    _git(worktree, "checkout", "-b", "automation/dsw-compat-review")
    compatibility_report = worktree / "docs" / "compatibility" / "unsupported-metamodels.md"
    compatibility_report.parent.mkdir(parents=True)
    compatibility_report.write_text(rendered_report.read_text(encoding="utf-8"), encoding="utf-8")
    _git(worktree, "add", "docs/compatibility/unsupported-metamodels.md")
    _git(worktree, "commit", "-m", "docs: record unsupported DSW metamodels")
    _git(worktree, "push", "-u", "origin", "automation/dsw-compat-review")
    existing_branch_commit = _git_output(worktree, "rev-parse", "automation/dsw-compat-review")

    _git(worktree, "checkout", "master")
    env = _fake_gh_env(tmp_path / "bin", log_path=gh_log)
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
            "automation/dsw-compat-review",
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
        _git_output(worktree, "rev-parse", "automation/dsw-compat-review") == existing_branch_commit
    )
    assert "pr view automation/dsw-compat-review" in gh_log.read_text(encoding="utf-8")
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
    """The DSW compatibility follow-up PR helper should expose a help screen."""

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
    assert "DSW compatibility follow-up" in result.stdout
    assert "--report" in result.stdout
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


def test_resolve_upstream_refs_expands_artifact_ranges(repo_root: Path) -> None:
    """The clean scaffold artifact range should include all supported tags."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_upstream_refs.py"),
            "--remote",
            "https://github.com/ds-wizard/science-europe-template.git",
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
    _git(worktree, "add", "README.md")
    _git(worktree, "commit", "-m", "base")
    _git(worktree, "remote", "add", "origin", str(origin))
    _git(worktree, "push", "-u", "origin", "master")


def _write_dsw_compat_discovery_report(path: Path) -> None:
    path.write_text(
        "## DSW Compatibility Discovery\n\n"
        "| Ref | Version | metamodelVersion | Runtime | Status |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `v1.31.0` | `v1.31.0` | `19.0` | - | unsupported |\n",
        encoding="utf-8",
    )


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


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
