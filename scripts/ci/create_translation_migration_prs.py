#!/usr/bin/env python3
"""Create pull requests that migrate translations between version branches."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dsw_document_template_tool.translation_migration import (  # noqa: E402
    TranslationRepositoryConfig,
    clean_artifact_version_paths,
    load_translation_repository_config,
    migration_branch,
    target_versions,
    version_branch,
    version_paths,
)

MERGE_REPORT_PATH = Path(".translation-tree") / "merge-report.json"
TRANSFORM_TEMPLATE_CLI = "src/transform_template.py"
TRANSLATION_TREE_CLI = "src/translation_tree.py"


@dataclass(frozen=True)
class MigrationResult:
    """Result of applying one source version to one target branch."""

    summary_path: Path
    source_merge_report: dict[str, object]


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Open conservative cross-version translation migration PRs.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Translation repository checkout containing translation-config.yml.",
    )
    parser.add_argument(
        "--tooling-root",
        required=True,
        help="Checked-out tooling repository.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml relative to --repo.",
    )
    parser.add_argument(
        "--source-version",
        required=True,
        help="Source version tag, for example v1.30.1.",
    )
    parser.add_argument(
        "--target-version",
        action="append",
        default=[],
        help=(
            "Target version tag. May be repeated. Defaults to versions whose "
            "version_policy.migrate_into value is auto."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run migrations locally but do not commit, push, or create pull requests.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push changed migration branches.",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create or update GitHub pull requests for pushed migration branches.",
    )
    parser.add_argument(
        "--tdk-executable",
        help="Path to dsw-tdk. Defaults to <tooling-root>/.venv/bin/dsw-tdk.",
    )
    parser.add_argument(
        "--clean-artifact-root",
        help=(
            "Downloaded clean upstream scaffold artifact root. When provided, "
            "target compact/expanded/fresh translation trees are copied from "
            "the artifact instead of being regenerated from checked-in compact templates."
        ),
    )
    return parser


def main() -> None:
    """Run migration PR creation."""

    args = build_argument_parser().parse_args()
    if args.create_pr and not args.push:
        raise SystemExit("--create-pr requires --push so the PR head branch exists remotely.")
    if args.clean_artifact_root and not Path(args.clean_artifact_root).is_dir():
        raise SystemExit(
            f"--clean-artifact-root does not exist or is not a directory: "
            f"{args.clean_artifact_root}"
        )

    repo = Path(args.repo).resolve()
    tooling_root = Path(args.tooling_root).resolve()
    config = load_translation_repository_config(repo / args.config)
    tdk_executable = (
        Path(args.tdk_executable).resolve()
        if args.tdk_executable
        else tooling_root / ".venv" / "bin" / "dsw-tdk"
    )
    clean_artifact_root = (
        Path(args.clean_artifact_root).resolve() if args.clean_artifact_root else None
    )

    _run(["git", "fetch", "--prune", "origin"], cwd=repo)

    migrated_targets = target_versions(
        config,
        args.source_version,
        requested_targets=args.target_version or None,
    )
    if not migrated_targets:
        print("INFO: No target versions to migrate.")
        return

    with tempfile.TemporaryDirectory(prefix="dsw-translation-migrate-") as temp_raw:
        temp_root = Path(temp_raw)
        for target_version in migrated_targets:
            migrate_one_target(
                repo=repo,
                tooling_root=tooling_root,
                tdk_executable=tdk_executable,
                config=config,
                source_version=args.source_version,
                target_version=target_version,
                temp_root=temp_root,
                clean_artifact_root=clean_artifact_root,
                dry_run=args.dry_run,
                push=args.push,
                create_pr=args.create_pr,
            )


def migrate_one_target(
    *,
    repo: Path,
    tooling_root: Path,
    tdk_executable: Path,
    config: TranslationRepositoryConfig,
    source_version: str,
    target_version: str,
    temp_root: Path,
    clean_artifact_root: Path | None,
    dry_run: bool,
    push: bool,
    create_pr: bool,
) -> None:
    """Migrate translations from one source version into one target branch."""

    source_branch = version_branch(config, source_version)
    target_branch = version_branch(config, target_version)
    bot_branch = migration_branch(config, source_version, target_version)
    case_root = temp_root / f"{source_version}-to-{target_version}"
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True)
    source_checkout = case_root / "source"
    target_checkout = case_root / "target"

    add_detached_remote_worktree(
        repo=repo,
        checkout=source_checkout,
        branch=source_branch,
    )
    add_detached_remote_worktree(
        repo=repo,
        checkout=target_checkout,
        branch=target_branch,
    )

    try:
        migration_result = refresh_target_with_source(
            source_checkout=source_checkout,
            target_checkout=target_checkout,
            tooling_root=tooling_root,
            tdk_executable=tdk_executable,
            config=config,
            source_version=source_version,
            target_version=target_version,
            temp_root=case_root,
            clean_artifact_root=clean_artifact_root,
        )
        migrated_units = int(migration_result.source_merge_report.get("migrated_units", 0))
        if migrated_units == 0:
            print(
                f"INFO: [{source_version} -> {target_version}] no source translations "
                "were migrated; skipping PR."
            )
            return

        changed_paths = _changed_paths(target_checkout)
        if not changed_paths:
            print(f"INFO: [{source_version} -> {target_version}] no changes.")
            return

        print(
            f"INFO: [{source_version} -> {target_version}] changed paths:\n"
            + "\n".join(f"  {path}" for path in changed_paths)
        )
        if dry_run:
            print(f"INFO: [{source_version} -> {target_version}] dry run; not committing.")
            return

        _run(
            ["git", "config", "user.name", "github-actions[bot]"],
            cwd=target_checkout,
        )
        _run(
            [
                "git",
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com",
            ],
            cwd=target_checkout,
        )
        _run(["git", "add", "--", *changed_paths], cwd=target_checkout)
        _run(
            [
                "git",
                "commit",
                "-m",
                f"chore(migrate): carry {source_version} translations to {target_version}",
            ],
            cwd=target_checkout,
        )

        if push:
            _run(
                ["git", "push", "--force-with-lease", "origin", f"HEAD:refs/heads/{bot_branch}"],
                cwd=target_checkout,
            )
        if create_pr:
            head_sha = _run_capture(["git", "rev-parse", "HEAD"], cwd=target_checkout).strip()
            create_or_update_pull_request(
                checkout=target_checkout,
                bot_branch=bot_branch,
                target_branch=target_branch,
                source_version=source_version,
                target_version=target_version,
                summary_path=migration_result.summary_path,
                head_sha=head_sha,
                auto_merge=is_auto_merge_safe(
                    config=config,
                    report=migration_result.source_merge_report,
                ),
            )
    finally:
        _run(["git", "worktree", "remove", "--force", str(source_checkout)], cwd=repo, check=False)
        _run(["git", "worktree", "remove", "--force", str(target_checkout)], cwd=repo, check=False)


def refresh_target_with_source(
    *,
    source_checkout: Path,
    target_checkout: Path,
    tooling_root: Path,
    tdk_executable: Path,
    config: TranslationRepositoryConfig,
    source_version: str,
    target_version: str,
    temp_root: Path,
    clean_artifact_root: Path | None,
) -> MigrationResult:
    """Refresh target workspace and fill blanks from the source tree."""

    source_paths = version_paths(config, source_version)
    target_paths = version_paths(config, target_version)
    fresh_tree = temp_root / "fresh-target-tree"
    preserved_tree = temp_root / "target-preserved-tree"
    merged_tree = temp_root / "merged-tree"
    source_tree = source_checkout / source_paths.translation_tree_dir
    target_tree = target_checkout / target_paths.translation_tree_dir

    if clean_artifact_root is not None:
        restore_clean_target_workspace(
            config=config,
            target_checkout=target_checkout,
            target_version=target_version,
            fresh_tree=fresh_tree,
            clean_artifact_root=clean_artifact_root,
        )
    else:
        _run_tool(
            tooling_root,
            TRANSFORM_TEMPLATE_CLI,
            "expand",
            "--source",
            target_checkout / target_paths.compact_template_dir,
            "--output",
            target_checkout / target_paths.expanded_template_dir,
        )
        _run_tool(
            tooling_root,
            TRANSLATION_TREE_CLI,
            "export",
            "--source",
            target_checkout / target_paths.expanded_template_dir,
            "--output",
            fresh_tree,
        )
    _merge_or_copy(
        tooling_root=tooling_root,
        old_tree=target_tree,
        new_tree=fresh_tree,
        output_tree=preserved_tree,
        config=config,
    )
    _merge_or_copy(
        tooling_root=tooling_root,
        old_tree=source_tree,
        new_tree=preserved_tree,
        output_tree=merged_tree,
        config=config,
    )

    if target_tree.exists():
        shutil.rmtree(target_tree)
    target_tree.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(merged_tree, target_tree)

    _run_tool(
        tooling_root,
        TRANSLATION_TREE_CLI,
        "audit",
        "--tree",
        target_tree,
        "--source",
        target_checkout / target_paths.expanded_template_dir,
    )
    _run_tool(
        tooling_root,
        TRANSLATION_TREE_CLI,
        "sync",
        "--tree",
        target_tree,
        "--source",
        target_checkout / target_paths.expanded_template_dir,
        "--output",
        target_checkout / target_paths.translated_template_dir,
        "--template-organization-id",
        config.translation.translated_template_organization_id,
        "--template-id",
        config.translation.translated_template_id,
        "--template-name",
        config.translation.translated_template_name,
        "--template-version",
        target_paths.version_number,
    )
    _run_tool(
        tooling_root,
        TRANSLATION_TREE_CLI,
        "audit-output",
        "--source",
        target_checkout / target_paths.expanded_template_dir,
        "--output",
        target_checkout / target_paths.translated_template_dir,
    )
    _run(
        [
            str(tdk_executable),
            "verify",
            str(target_checkout / target_paths.translated_template_dir),
        ]
    )
    (target_checkout / target_paths.translated_template_package.parent).mkdir(
        parents=True,
        exist_ok=True,
    )
    _run(
        [
            str(tdk_executable),
            "package",
            str(target_checkout / target_paths.translated_template_dir),
            "--output",
            str(target_checkout / target_paths.translated_template_package),
            "--force",
        ]
    )

    source_merge_report = _read_json(merged_tree / MERGE_REPORT_PATH)
    summary_path = (
        target_checkout
        / target_paths.migration_report_dir
        / (f"{source_version}-to-{target_version}.md")
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        render_summary(
            source_version=source_version,
            target_version=target_version,
            source_branch=version_branch(config, source_version),
            target_branch=version_branch(config, target_version),
            report=source_merge_report,
        ),
        encoding="utf-8",
    )
    return MigrationResult(
        summary_path=summary_path,
        source_merge_report=source_merge_report,
    )


def restore_clean_target_workspace(
    *,
    config: TranslationRepositoryConfig,
    target_checkout: Path,
    target_version: str,
    fresh_tree: Path,
    clean_artifact_root: Path,
) -> None:
    """Restore generated target workspace inputs from a clean scaffold artifact."""

    target_paths = version_paths(config, target_version)
    artifact_paths = clean_artifact_version_paths(
        config=config,
        version=target_version,
        artifact_root=clean_artifact_root,
    )
    required_dirs = (
        artifact_paths.compact_template_dir,
        artifact_paths.expanded_template_dir,
        artifact_paths.translation_tree_dir,
    )
    missing_dirs = [path for path in required_dirs if not path.is_dir()]
    if missing_dirs:
        missing = "\n".join(f"- {path}" for path in missing_dirs)
        raise SystemExit(
            f"Clean artifact root does not contain required {target_version} paths:\n{missing}"
        )

    _replace_tree(
        artifact_paths.compact_template_dir,
        target_checkout / target_paths.compact_template_dir,
    )
    _replace_tree(
        artifact_paths.expanded_template_dir,
        target_checkout / target_paths.expanded_template_dir,
    )
    _replace_tree(artifact_paths.translation_tree_dir, fresh_tree)


def _replace_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def _merge_or_copy(
    *,
    tooling_root: Path,
    old_tree: Path,
    new_tree: Path,
    output_tree: Path,
    config: TranslationRepositoryConfig,
) -> None:
    if old_tree.joinpath(MERGE_REPORT_PATH.parent, "manifest.json").is_file():
        _run_tool(
            tooling_root,
            TRANSLATION_TREE_CLI,
            "merge",
            "--old-tree",
            old_tree,
            "--new-tree",
            new_tree,
            "--output",
            output_tree,
            "--source-lang",
            config.translation.source_language,
            "--target-lang",
            config.translation.target_language,
        )
        return
    if output_tree.exists():
        shutil.rmtree(output_tree)
    shutil.copytree(new_tree, output_tree)


def render_summary(
    *,
    source_version: str,
    target_version: str,
    source_branch: str,
    target_branch: str,
    report: dict[str, object],
) -> str:
    """Render a stable markdown migration report."""

    lines = [
        f"# Translation Migration: {source_version} -> {target_version}",
        "",
        f"- Source branch: `{source_branch}`",
        f"- Target branch: `{target_branch}`",
        "- Policy: exact key/source hash only; unsafe or non-exact units stay empty.",
        "",
        "## Merge Report",
        "",
        f"- Total units: {report.get('total_units', 0)}",
        f"- Preserved target translations: {report.get('preserved_units', 0)}",
        f"- Migrated source translations: {report.get('migrated_units', 0)}",
        f"- Untranslated units: {report.get('untranslated_units', 0)}",
        f"- Skipped unsafe old translations: {report.get('skipped_unsafe_old_units', 0)}",
        f"- Exact key matches: {report.get('exact_key_matches', 0)}",
        f"- Source hash matches: {report.get('source_hash_matches', 0)}",
        f"- Sentence matches: {report.get('sentence_matches', 0)}",
        "",
    ]
    return "\n".join(lines)


def create_or_update_pull_request(
    *,
    checkout: Path,
    bot_branch: str,
    target_branch: str,
    source_version: str,
    target_version: str,
    summary_path: Path,
    head_sha: str,
    auto_merge: bool,
) -> None:
    """Create or update one migration pull request."""

    title = f"chore: migrate {source_version} translations to {target_version}"
    existing_number = find_pull_request_number(
        checkout=checkout,
        bot_branch=bot_branch,
        target_branch=target_branch,
    )
    if existing_number:
        _run_pr_command(
            [
                "gh",
                "pr",
                "edit",
                existing_number,
                "--title",
                title,
                "--body-file",
                str(summary_path),
            ],
            checkout=checkout,
            bot_branch=bot_branch,
            target_branch=target_branch,
        )
        if auto_merge:
            enable_auto_merge(
                checkout=checkout,
                pull_request_number=existing_number,
                head_sha=head_sha,
                bot_branch=bot_branch,
                target_branch=target_branch,
            )
        return

    _run_pr_command(
        [
            "gh",
            "pr",
            "create",
            "--base",
            target_branch,
            "--head",
            bot_branch,
            "--title",
            title,
            "--body-file",
            str(summary_path),
        ],
        checkout=checkout,
        bot_branch=bot_branch,
        target_branch=target_branch,
    )
    new_number = find_pull_request_number(
        checkout=checkout,
        bot_branch=bot_branch,
        target_branch=target_branch,
    )
    if auto_merge and new_number:
        enable_auto_merge(
            checkout=checkout,
            pull_request_number=new_number,
            head_sha=head_sha,
            bot_branch=bot_branch,
            target_branch=target_branch,
        )


def find_pull_request_number(*, checkout: Path, bot_branch: str, target_branch: str) -> str:
    """Return an open pull request number for the migration branch when present."""

    return _run_capture(
        [
            "gh",
            "pr",
            "list",
            "--head",
            bot_branch,
            "--base",
            target_branch,
            "--state",
            "open",
            "--json",
            "number",
            "--jq",
            ".[0].number // empty",
        ],
        cwd=checkout,
    ).strip()


def add_detached_remote_worktree(*, repo: Path, checkout: Path, branch: str) -> None:
    """Add a detached worktree from ``origin/<branch>``.

    Migration runs generate temporary commits and push HEAD to an automation
    branch. They do not need a local branch checkout, and avoiding one prevents
    stale local automation branches or already-open worktrees from blocking CI.
    """

    if not remote_branch_exists(repo=repo, branch=branch):
        raise SystemExit(f"Remote branch does not exist: origin/{branch}")
    _run(["git", "worktree", "add", "--detach", str(checkout), f"origin/{branch}"], cwd=repo)


def remote_branch_exists(*, repo: Path, branch: str) -> bool:
    """Return whether ``origin/<branch>`` exists."""

    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def is_auto_merge_safe(
    *,
    config: TranslationRepositoryConfig,
    report: dict[str, object],
) -> bool:
    """Return whether the generated migration is safe to request auto-merge."""

    if not config.migration.auto_merge_when_clean:
        return False
    if config.migration.mode != "exact-only":
        return False
    if config.migration.non_exact_policy != "leave_empty_needs_translation":
        return False
    if int(report.get("migrated_units", 0)) <= 0:
        return False
    return int(report.get("sentence_matches", 0)) == 0


def enable_auto_merge(
    *,
    checkout: Path,
    pull_request_number: str,
    head_sha: str,
    bot_branch: str,
    target_branch: str,
) -> None:
    """Ask GitHub to merge the migration PR once repository requirements pass."""

    result = _run(
        [
            "gh",
            "pr",
            "merge",
            pull_request_number,
            "--squash",
            "--auto",
            "--delete-branch",
            "--match-head-commit",
            head_sha,
        ],
        cwd=checkout,
        check=False,
    )
    if result.returncode == 0:
        append_github_summary(
            [
                "## Migration PR auto-merge requested",
                "",
                f"- Pull request: `#{pull_request_number}`",
                f"- Base branch: `{target_branch}`",
                f"- Head branch: `{bot_branch}`",
                f"- Head SHA: `{head_sha}`",
                "",
            ]
        )
        return

    immediate_merge_result = _run(
        [
            "gh",
            "pr",
            "merge",
            pull_request_number,
            "--squash",
            "--delete-branch",
            "--match-head-commit",
            head_sha,
        ],
        cwd=checkout,
        check=False,
    )
    if immediate_merge_result.returncode == 0:
        append_github_summary(
            [
                "## Migration PR merged",
                "",
                "GitHub did not accept an auto-merge request, so the workflow "
                "merged the exact-only migration PR directly after local "
                "migration audits passed.",
                "",
                f"- Pull request: `#{pull_request_number}`",
                f"- Base branch: `{target_branch}`",
                f"- Head branch: `{bot_branch}`",
                f"- Head SHA: `{head_sha}`",
                "",
            ]
        )
        return

    manual_url = manual_pull_request_url(base_branch=target_branch, head_branch=bot_branch)
    append_github_summary(
        [
            "## Migration PR was not merged",
            "",
            "GitHub rejected both the auto-merge request and the immediate merge. "
            "The migration PR still exists and can be reviewed or merged manually.",
            "",
            f"- Pull request: `#{pull_request_number}`",
            f"- Base branch: `{target_branch}`",
            f"- Head branch: `{bot_branch}`",
            f"- Manual PR URL: {manual_url}",
            "",
        ]
    )
    print(
        "WARNING: Could not merge migration PR automatically. "
        f"Review or merge manually if needed: {manual_url}",
        file=sys.stderr,
    )


def _run_pr_command(
    args: list[str],
    *,
    checkout: Path,
    bot_branch: str,
    target_branch: str,
) -> None:
    """Run a GitHub PR mutation, downgrading permission failures to warnings."""

    result = _run(args, cwd=checkout, check=False)
    if result.returncode == 0:
        return

    manual_url = manual_pull_request_url(base_branch=target_branch, head_branch=bot_branch)
    append_github_summary(
        [
            "## Migration PR needs manual creation",
            "",
            "GitHub Actions pushed the migration branch, but this repository "
            "does not allow Actions to create or update pull requests.",
            "",
            f"- Base branch: `{target_branch}`",
            f"- Head branch: `{bot_branch}`",
            f"- Manual PR URL: {manual_url}",
            "",
        ]
    )
    print(
        "WARNING: Could not create or update migration PR. The migration branch "
        f"was pushed successfully; open the PR manually if needed: {manual_url}",
        file=sys.stderr,
    )


def manual_pull_request_url(*, base_branch: str, head_branch: str) -> str:
    """Build a manual PR URL for environments where Actions cannot create PRs."""

    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        return f"{head_branch} -> {base_branch}"
    return (
        f"{server_url}/{repository}/compare/"
        f"{quote(base_branch, safe='')}...{quote(head_branch, safe='')}?expand=1"
    )


def append_github_summary(lines: list[str]) -> None:
    """Append lines to the GitHub step summary when running in Actions."""

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(lines))
        summary_file.write("\n")


def _run_tool(tooling_root: Path, script: str, *args: object) -> None:
    _run(
        [
            str(tooling_root / ".venv" / "bin" / "python"),
            str(tooling_root / script),
            *map(str, args),
        ]
    )


def _run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(args))
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        check=check,
    )


def _run_capture(args: list[str], *, cwd: Path | None = None) -> str:
    print("+ " + " ".join(args))
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def _changed_paths(checkout: Path) -> list[str]:
    output = _run_capture(["git", "status", "--short"], cwd=checkout)
    paths: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        paths.append(line[3:])
    return paths


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
