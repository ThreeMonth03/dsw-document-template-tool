#!/usr/bin/env python3
"""Synchronize translation version branches from clean scaffold artifacts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dsw_document_template_tool.translation_migration import (  # noqa: E402
    TranslationRepositoryConfig,
    clean_artifact_version_paths,
    clean_artifact_versions,
    load_translation_repository_config,
    sorted_versions,
    version_branch,
    version_paths,
)


@dataclass(frozen=True)
class SyncResult:
    """Result of one version-branch sync run."""

    previous_latest_version: str
    current_latest_version: str
    added_versions: tuple[str, ...]
    created_branches: tuple[str, ...]
    config_changed: bool


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Create missing translation version branches from clean artifacts.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Translation repository checkout containing translation-config.yml.",
    )
    parser.add_argument(
        "--tooling-root",
        required=True,
        help="Checked-out DSW-document-template-tool repository.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml relative to --repo.",
    )
    parser.add_argument(
        "--clean-artifact-root",
        required=True,
        help="Downloaded clean upstream scaffold artifact root.",
    )
    parser.add_argument(
        "--tdk-executable",
        help="Path to dsw-tdk. Defaults to <tooling-root>/.venv/bin/dsw-tdk.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push updated master config and newly created translation branches.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without committing, pushing, or creating branches.",
    )
    parser.add_argument(
        "--github-output",
        help="Optional GitHub Actions output file to write sync metadata to.",
    )
    return parser


def main() -> None:
    """Run translation version branch synchronization."""

    args = build_argument_parser().parse_args()
    repo = Path(args.repo).resolve()
    tooling_root = Path(args.tooling_root).resolve()
    config_path = repo / args.config
    clean_artifact_root = Path(args.clean_artifact_root).resolve()
    tdk_executable = (
        Path(args.tdk_executable).resolve()
        if args.tdk_executable
        else tooling_root / ".venv" / "bin" / "dsw-tdk"
    )

    result = sync_translation_versions(
        repo=repo,
        tooling_root=tooling_root,
        config_path=config_path,
        clean_artifact_root=clean_artifact_root,
        tdk_executable=tdk_executable,
        push=args.push,
        dry_run=args.dry_run,
    )
    print_summary(result)
    if args.github_output:
        write_github_output(Path(args.github_output), result)


def sync_translation_versions(
    *,
    repo: Path,
    tooling_root: Path,
    config_path: Path,
    clean_artifact_root: Path,
    tdk_executable: Path,
    push: bool,
    dry_run: bool,
) -> SyncResult:
    """Update supported versions and create missing version branches."""

    config = load_translation_repository_config(config_path)
    existing_versions = tuple(config.template.supported_versions)
    previous_latest = existing_versions[-1]
    artifact_versions = tuple(
        clean_artifact_versions(config=config, artifact_root=clean_artifact_root)
    )
    if not artifact_versions:
        raise SystemExit(
            f"No clean artifact versions found under {clean_artifact_root}. "
            "Did the tooling workflow upload clean-upstream-version-artifacts?"
        )

    supported_versions = tuple(sorted_versions(list({*existing_versions, *artifact_versions})))
    added_versions = tuple(
        version for version in supported_versions if version not in existing_versions
    )
    current_latest = supported_versions[-1]
    config_changed = supported_versions != existing_versions

    if config_changed:
        if dry_run:
            print(
                "INFO: dry-run would update supported_versions to: " + ", ".join(supported_versions)
            )
        else:
            write_supported_versions(config_path, supported_versions)
            ensure_git_identity(repo)
            _run(["git", "add", str(config_path.relative_to(repo))], cwd=repo)
            _run(
                [
                    "git",
                    "commit",
                    "-m",
                    "chore: sync supported template versions",
                ],
                cwd=repo,
            )
            if push:
                _run(["git", "push", "origin", "HEAD:master"], cwd=repo)
            config = load_translation_repository_config(config_path)

    _run(["git", "fetch", "--prune", "origin"], cwd=repo)
    created_branches: list[str] = []
    with tempfile.TemporaryDirectory(prefix="dsw-version-branch-sync-") as temp_raw:
        temp_root = Path(temp_raw)
        for version in supported_versions:
            branch = version_branch(config, version)
            if remote_branch_exists(repo, branch):
                continue
            created_branches.append(branch)
            if dry_run:
                print(f"INFO: dry-run would create {branch}")
                continue
            create_version_branch(
                repo=repo,
                tooling_root=tooling_root,
                tdk_executable=tdk_executable,
                config=config,
                version=version,
                branch=branch,
                clean_artifact_root=clean_artifact_root,
                temp_root=temp_root,
                push=push,
            )

    return SyncResult(
        previous_latest_version=previous_latest,
        current_latest_version=current_latest,
        added_versions=added_versions,
        created_branches=tuple(created_branches),
        config_changed=config_changed,
    )


def create_version_branch(
    *,
    repo: Path,
    tooling_root: Path,
    tdk_executable: Path,
    config: TranslationRepositoryConfig,
    version: str,
    branch: str,
    clean_artifact_root: Path,
    temp_root: Path,
    push: bool,
) -> None:
    """Create and initialize one missing translation version branch."""

    checkout = temp_root / branch.replace("/", "-")
    if checkout.exists():
        shutil.rmtree(checkout)
    _run(["git", "worktree", "add", "-B", branch, str(checkout), "HEAD"], cwd=repo)
    try:
        restore_clean_workspace(
            checkout=checkout,
            config=config,
            version=version,
            clean_artifact_root=clean_artifact_root,
        )
        sync_blank_translation_output(
            checkout=checkout,
            tooling_root=tooling_root,
            tdk_executable=tdk_executable,
            config=config,
            version=version,
        )
        ensure_git_identity(checkout)
        _run(["git", "add", "."], cwd=checkout)
        if not has_staged_changes(checkout):
            print(f"INFO: [{branch}] no changes after initialization.")
            return
        _run(
            ["git", "commit", "-m", f"chore: initialize {version} translation scaffold"],
            cwd=checkout,
        )
        if push:
            _run(["git", "push", "origin", f"HEAD:{branch}"], cwd=checkout)
    finally:
        _run(["git", "worktree", "remove", "--force", str(checkout)], cwd=repo, check=False)


def restore_clean_workspace(
    *,
    checkout: Path,
    config: TranslationRepositoryConfig,
    version: str,
    clean_artifact_root: Path,
) -> None:
    """Copy clean compact/expanded/translation trees into a version branch."""

    target_paths = version_paths(config, version)
    artifact_paths = clean_artifact_version_paths(
        config=config,
        version=version,
        artifact_root=clean_artifact_root,
    )
    required_dirs = (
        artifact_paths.compact_template_dir,
        artifact_paths.expanded_template_dir,
        artifact_paths.translation_tree_dir,
    )
    missing = [path for path in required_dirs if not path.is_dir()]
    if missing:
        raise SystemExit(
            "Clean artifact root does not contain required paths for "
            f"{version}:\n" + "\n".join(f"- {path}" for path in missing)
        )

    replace_tree(artifact_paths.compact_template_dir, checkout / target_paths.compact_template_dir)
    replace_tree(
        artifact_paths.expanded_template_dir,
        checkout / target_paths.expanded_template_dir,
    )
    replace_tree(artifact_paths.translation_tree_dir, checkout / target_paths.translation_tree_dir)


def sync_blank_translation_output(
    *,
    checkout: Path,
    tooling_root: Path,
    tdk_executable: Path,
    config: TranslationRepositoryConfig,
    version: str,
) -> None:
    """Generate a valid fallback translated template package for one branch."""

    paths = version_paths(config, version)
    _run_tool(
        tooling_root,
        "src/translation_tree.py",
        "audit",
        "--tree",
        checkout / paths.translation_tree_dir,
        "--source",
        checkout / paths.expanded_template_dir,
    )
    _run_tool(
        tooling_root,
        "src/translation_tree.py",
        "sync",
        "--tree",
        checkout / paths.translation_tree_dir,
        "--source",
        checkout / paths.expanded_template_dir,
        "--output",
        checkout / paths.translated_template_dir,
        "--template-organization-id",
        config.translation.translated_template_organization_id,
        "--template-id",
        config.translation.translated_template_id,
        "--template-name",
        config.translation.translated_template_name,
        "--template-version",
        paths.version_number,
    )
    _run_tool(
        tooling_root,
        "src/translation_tree.py",
        "audit-output",
        "--source",
        checkout / paths.expanded_template_dir,
        "--output",
        checkout / paths.translated_template_dir,
    )
    _run([str(tdk_executable), "verify", str(checkout / paths.translated_template_dir)])
    (checkout / paths.translated_template_package.parent).mkdir(parents=True, exist_ok=True)
    _run(
        [
            str(tdk_executable),
            "package",
            str(checkout / paths.translated_template_dir),
            "--output",
            str(checkout / paths.translated_template_package),
            "--force",
        ]
    )


def write_supported_versions(config_path: Path, versions: tuple[str, ...]) -> None:
    """Update the configured supported version list."""

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    payload["template"]["supported_versions"] = list(versions)
    config_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def write_github_output(path: Path, result: SyncResult) -> None:
    """Write GitHub Actions step outputs."""

    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"previous_latest_version={result.previous_latest_version}\n")
        handle.write(f"current_latest_version={result.current_latest_version}\n")
        handle.write(f"added_versions={' '.join(result.added_versions)}\n")
        handle.write(f"created_branches={' '.join(result.created_branches)}\n")
        handle.write(f"config_changed={str(result.config_changed).lower()}\n")


def print_summary(result: SyncResult) -> None:
    """Print a concise human-readable sync summary."""

    print("INFO: translation version sync complete")
    print(f"INFO: previous latest version: {result.previous_latest_version}")
    print(f"INFO: current latest version: {result.current_latest_version}")
    print(f"INFO: added versions: {', '.join(result.added_versions) or '(none)'}")
    print(f"INFO: created branches: {', '.join(result.created_branches) or '(none)'}")
    print(f"INFO: config changed: {result.config_changed}")


def remote_branch_exists(repo: Path, branch: str) -> bool:
    """Return whether ``origin/<branch>`` exists."""

    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def replace_tree(source: Path, destination: Path) -> None:
    """Replace one directory tree."""

    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def ensure_git_identity(repo: Path) -> None:
    """Configure the standard GitHub Actions bot identity."""

    _run(["git", "config", "user.name", "github-actions[bot]"], cwd=repo)
    _run(
        [
            "git",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        cwd=repo,
    )


def has_staged_changes(repo: Path) -> bool:
    """Return whether the index contains staged changes."""

    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo,
        check=False,
    )
    return result.returncode != 0


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


if __name__ == "__main__":
    main()
