#!/usr/bin/env python3
"""Synchronize translation version branches from clean scaffold artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
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
    preview_runtime_for_version,
    sorted_versions,
    version_branch,
    version_paths,
)

BRANCH_LOCAL_DEMO_ASSET_DIRS = (
    Path("workspace") / "knowledge-models",
    Path("workspace") / "projects",
)


@dataclass(frozen=True)
class SyncResult:
    """Result of one version-branch sync run."""

    previous_latest_version: str
    current_latest_version: str
    added_versions: tuple[str, ...]
    created_branches: tuple[str, ...]
    refreshed_branches: tuple[str, ...]
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
        "--refresh-existing",
        action="store_true",
        help=(
            "Refresh existing translation version branches from clean artifacts, "
            "preserving exact-match translations."
        ),
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
        refresh_existing=args.refresh_existing,
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
    refresh_existing: bool = False,
) -> SyncResult:
    """Update supported versions and synchronize version branches."""

    config = load_translation_repository_config(config_path)
    existing_versions = tuple(config.template.supported_versions)
    previous_latest = sorted_versions(existing_versions)[-1]
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
            config = replace(
                config,
                template=replace(config.template, supported_versions=supported_versions),
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
    refreshed_branches: list[str] = []
    with tempfile.TemporaryDirectory(prefix="dsw-version-branch-sync-") as temp_raw:
        temp_root = Path(temp_raw)
        for version in supported_versions:
            branch = version_branch(config, version)
            branch_exists = remote_branch_exists(repo, branch)
            if branch_exists and refresh_existing:
                if dry_run:
                    print(f"INFO: dry-run would refresh {branch}")
                    refreshed_branches.append(branch)
                    continue
                if refresh_version_branch(
                    repo=repo,
                    tooling_root=tooling_root,
                    tdk_executable=tdk_executable,
                    config=config,
                    version=version,
                    branch=branch,
                    clean_artifact_root=clean_artifact_root,
                    temp_root=temp_root,
                    push=push,
                ):
                    refreshed_branches.append(branch)
                continue
            if branch_exists:
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
        refreshed_branches=tuple(refreshed_branches),
        config_changed=config_changed,
    )


def refresh_version_branch(
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
) -> bool:
    """Refresh one existing translation branch from the latest clean artifact."""

    checkout = temp_root / branch.replace("/", "-")
    preserved_tree = temp_root / f"{branch.replace('/', '-')}-preserved-tree"
    merged_tree = temp_root / f"{branch.replace('/', '-')}-merged-tree"
    if checkout.exists():
        shutil.rmtree(checkout)
    if preserved_tree.exists():
        shutil.rmtree(preserved_tree)
    if merged_tree.exists():
        shutil.rmtree(merged_tree)

    _run(["git", "worktree", "add", "-B", branch, str(checkout), f"origin/{branch}"], cwd=repo)
    try:
        paths = version_paths(config, version)
        existing_translation_tree = checkout / paths.translation_tree_dir
        had_existing_translation_tree = existing_translation_tree.is_dir()
        if had_existing_translation_tree:
            shutil.copytree(existing_translation_tree, preserved_tree)

        restore_clean_workspace(
            checkout=checkout,
            config=config,
            version=version,
            clean_artifact_root=clean_artifact_root,
        )
        if had_existing_translation_tree:
            merge_preserved_translations(
                checkout=checkout,
                tooling_root=tooling_root,
                config=config,
                version=version,
                preserved_tree=preserved_tree,
                merged_tree=merged_tree,
            )
        sync_blank_translation_output(
            checkout=checkout,
            tooling_root=tooling_root,
            tdk_executable=tdk_executable,
            config=config,
            version=version,
        )
        write_version_branch_workflow(
            checkout=checkout,
            tooling_root=tooling_root,
            config=config,
            version=version,
            branch=branch,
        )
        ensure_git_identity(checkout)
        _run(["git", "add", "."], cwd=checkout)
        staged_paths = tuple(staged_changed_paths(checkout))
        package_path = paths.translated_template_package.as_posix()
        if staged_paths == (package_path,):
            _run(["git", "restore", "--staged", "--worktree", "--", package_path], cwd=checkout)
            print(f"INFO: [{branch}] only package metadata changed; skipping commit.")
            return False
        if not staged_paths:
            print(f"INFO: [{branch}] no changes after refresh.")
            return False
        _run(
            ["git", "commit", "-m", f"chore: refresh {version} translation scaffold"],
            cwd=checkout,
        )
        if push:
            _run(["git", "push", "origin", f"HEAD:{branch}"], cwd=checkout)
        return True
    finally:
        _run(["git", "worktree", "remove", "--force", str(checkout)], cwd=repo, check=False)


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
        write_version_branch_workflow(
            checkout=checkout,
            tooling_root=tooling_root,
            config=config,
            version=version,
            branch=branch,
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
    remove_branch_local_demo_assets(checkout)


def remove_branch_local_demo_assets(checkout: Path) -> None:
    """Remove stale demo fixtures from translation version branches.

    Version branches should use the demo KM/project checked out from the tooling
    repository by their workflow. Keeping copies in downstream branches makes
    preview artifacts depend on whichever stale fixture happened to be committed
    there.
    """

    for relative_dir in BRANCH_LOCAL_DEMO_ASSET_DIRS:
        path = checkout / relative_dir
        if path.exists():
            shutil.rmtree(path)


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


def write_version_branch_workflow(
    *,
    checkout: Path,
    tooling_root: Path,
    config: TranslationRepositoryConfig,
    version: str,
    branch: str,
) -> None:
    """Write the version-specific translation sync workflow into a branch checkout."""

    workflow = render_version_branch_workflow(
        tooling_root=tooling_root,
        config=config,
        version=version,
        branch=branch,
    )
    target = checkout / ".github" / "workflows" / "document_template_translation_sync.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(workflow, encoding="utf-8")


def render_version_branch_workflow(
    *,
    tooling_root: Path,
    config: TranslationRepositoryConfig,
    version: str,
    branch: str,
) -> str:
    """Render a version-specific translation sync workflow."""

    paths = version_paths(config, version)
    runtime = preview_runtime_for_version(version)
    source = tooling_root / "examples" / "github-actions" / "document_template_translation_sync.yml"
    workflow = source.read_text(encoding="utf-8")

    replacements = {
        'pull_request:\n    branches: ["master"]': (
            f'pull_request:\n    branches: ["{branch}"]\n  push:\n    branches: ["{branch}"]'
        ),
        "github.event_name == 'schedule' ||": (
            "github.event_name == 'push' ||\n      github.event_name == 'schedule' ||"
        ),
        "TOOLING_REPOSITORY: ThreeMonth03/DSW-document-template-tool": _workflow_env_line(
            "TOOLING_REPOSITORY",
            config.tooling.repository,
        ),
        "TOOLING_REF: master": _workflow_env_line("TOOLING_REF", config.tooling.ref),
        "COMPACT_TEMPLATE_DIR: workspace/document-templates/compact/dsw-science-europe-1.30.0": (
            _workflow_env_line("COMPACT_TEMPLATE_DIR", paths.compact_template_dir.as_posix())
        ),
        "EXPANDED_TEMPLATE_DIR: workspace/document-templates/expanded/dsw-science-europe-1.30.0": (
            _workflow_env_line("EXPANDED_TEMPLATE_DIR", paths.expanded_template_dir.as_posix())
        ),
        (
            "TRANSLATION_TREE_DIR: workspace/document-templates/translation/"
            "dsw-science-europe-1.30.0"
        ): _workflow_env_line("TRANSLATION_TREE_DIR", paths.translation_tree_dir.as_posix()),
        "TRANSLATED_TEMPLATE_ORGANIZATION_ID: dsw": _workflow_env_line(
            "TRANSLATED_TEMPLATE_ORGANIZATION_ID",
            config.translation.translated_template_organization_id,
        ),
        "TRANSLATED_TEMPLATE_ID: science-europe-zh-hant": _workflow_env_line(
            "TRANSLATED_TEMPLATE_ID",
            config.translation.translated_template_id,
        ),
        "TRANSLATED_TEMPLATE_VERSION: 1.30.0": (
            _workflow_env_line("TRANSLATED_TEMPLATE_VERSION", paths.version_number)
        ),
        "TRANSLATED_TEMPLATE_NAME: Science Europe DMP Template (zh-Hant)": (
            _workflow_env_line(
                "TRANSLATED_TEMPLATE_NAME",
                config.translation.translated_template_name,
            )
        ),
        "TRANSLATION_SOURCE_LANG: en": _workflow_env_line(
            "TRANSLATION_SOURCE_LANG",
            config.translation.source_language,
        ),
        "TRANSLATION_TARGET_LANG: zh_Hant": _workflow_env_line(
            "TRANSLATION_TARGET_LANG",
            config.translation.target_language,
        ),
        'DSW_VERSION: "4.30"': _workflow_env_line("DSW_VERSION", runtime.dsw_version),
        'DSW_TDK_VERSION: "4.30.2"': _workflow_env_line(
            "DSW_TDK_VERSION",
            runtime.tdk_version,
        ),
        'UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION: "18.0"': (
            _workflow_env_line(
                "UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION",
                runtime.metamodel_version,
            )
        ),
        'UPSTREAM_TEMPLATE_PREVIEW_STRICT: "true"': (
            _workflow_env_line(
                "UPSTREAM_TEMPLATE_PREVIEW_STRICT",
                str(runtime.strict_project_preview).lower(),
            )
        ),
        (
            "TRANSLATED_TEMPLATE_DIR: outputs/document-templates/dsw-science-europe/"
            "v1.30.0/zh-Hant/dsw-science-europe-zh-hant-1.30.0"
        ): _workflow_env_line("TRANSLATED_TEMPLATE_DIR", paths.translated_template_dir.as_posix()),
        (
            "TRANSLATED_TEMPLATE_PACKAGE: outputs/document-templates/dsw-science-europe/"
            "v1.30.0/zh-Hant/dsw-science-europe-zh-hant-1.30.0.zip"
        ): _workflow_env_line(
            "TRANSLATED_TEMPLATE_PACKAGE",
            paths.translated_template_package.as_posix(),
        ),
        (
            "PROJECT_RENDER_OUTPUT: outputs/project-render/dsw-science-europe/"
            "v1.30.0/zh-Hant/test-project.pdf"
        ): _workflow_env_line(
            "PROJECT_RENDER_OUTPUT",
            (
                f"outputs/project-render/{paths.source_template_id}/{version}/"
                f"{config.translation.target_language_label}/test-project.pdf"
            ),
        ),
    }
    for old, new in replacements.items():
        workflow = replace_once(workflow, old, new)
    workflow = replace_count(
        workflow,
        "github.event.pull_request.head.ref || 'master'",
        f"github.event.pull_request.head.ref || '{branch}'",
        expected_count=3,
    )

    validate_version_branch_workflow(
        workflow,
        config=config,
        version=version,
        branch=branch,
    )
    return workflow


def validate_version_branch_workflow(
    workflow: str,
    *,
    config: TranslationRepositoryConfig,
    version: str,
    branch: str,
) -> None:
    """Validate a generated version-branch workflow before committing it."""

    paths = version_paths(config, version)
    runtime = preview_runtime_for_version(version)
    payload = yaml.safe_load(workflow)
    if not isinstance(payload, dict):
        raise SystemExit("Generated translation workflow must be a YAML mapping")

    trigger_payload = payload.get("on", payload.get(True))
    if not isinstance(trigger_payload, dict):
        raise SystemExit("Generated translation workflow must define mapping triggers")
    _expect_branch_trigger(trigger_payload, "pull_request", branch)
    _expect_branch_trigger(trigger_payload, "push", branch)
    for trigger_name in ("workflow_dispatch", "schedule"):
        if trigger_name not in trigger_payload:
            raise SystemExit(f"Generated translation workflow is missing {trigger_name!r} trigger")

    env = payload.get("env")
    if not isinstance(env, dict):
        raise SystemExit("Generated translation workflow must define mapping env")
    expected_env = {
        "TOOLING_REPOSITORY": config.tooling.repository,
        "TOOLING_REF": config.tooling.ref,
        "COMPACT_TEMPLATE_DIR": paths.compact_template_dir.as_posix(),
        "EXPANDED_TEMPLATE_DIR": paths.expanded_template_dir.as_posix(),
        "TRANSLATION_TREE_DIR": paths.translation_tree_dir.as_posix(),
        "TRANSLATED_TEMPLATE_ORGANIZATION_ID": (
            config.translation.translated_template_organization_id
        ),
        "TRANSLATED_TEMPLATE_ID": config.translation.translated_template_id,
        "TRANSLATED_TEMPLATE_VERSION": paths.version_number,
        "TRANSLATED_TEMPLATE_NAME": config.translation.translated_template_name,
        "TRANSLATION_SOURCE_LANG": config.translation.source_language,
        "TRANSLATION_TARGET_LANG": config.translation.target_language,
        "TRANSLATED_TEMPLATE_DIR": paths.translated_template_dir.as_posix(),
        "TRANSLATED_TEMPLATE_PACKAGE": paths.translated_template_package.as_posix(),
        "PROJECT_REF": "tooling-repo/workspace/projects/test-project.json",
        "PROJECT_RENDER_OUTPUT": (
            f"outputs/project-render/{paths.source_template_id}/{version}/"
            f"{config.translation.target_language_label}/test-project.pdf"
        ),
        "DSW_VERSION": runtime.dsw_version,
        "DSW_TDK_VERSION": runtime.tdk_version,
        "UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION": runtime.metamodel_version,
        "UPSTREAM_TEMPLATE_PREVIEW_STRICT": str(runtime.strict_project_preview).lower(),
    }
    for key, expected_value in expected_env.items():
        actual_value = env.get(key)
        if actual_value != expected_value:
            raise SystemExit(
                f"Generated translation workflow env {key}={actual_value!r}; "
                f"expected {expected_value!r}"
            )

    for forbidden_key in ("PUBLISH_TARGET_REPOSITORY", "PUBLISH_TARGET_BRANCH"):
        if forbidden_key in env or forbidden_key in workflow:
            raise SystemExit(f"Generated version-branch workflow must not contain {forbidden_key}")
    if "github.event.pull_request.head.ref || 'master'" in workflow:
        raise SystemExit("Generated version-branch workflow still falls back to master")
    if "github.event_name == 'push'" not in workflow:
        raise SystemExit("Generated version-branch workflow must handle push events")


def _expect_branch_trigger(
    trigger_payload: dict[object, object],
    trigger_name: str,
    branch: str,
) -> None:
    trigger = trigger_payload.get(trigger_name)
    if not isinstance(trigger, dict):
        raise SystemExit(
            f"Generated translation workflow trigger {trigger_name!r} must be a mapping"
        )
    branches = trigger.get("branches")
    if branches != [branch]:
        raise SystemExit(
            f"Generated translation workflow trigger {trigger_name!r} branches are "
            f"{branches!r}; expected {[branch]!r}"
        )


def _workflow_env_line(key: str, value: str) -> str:
    return f"{key}: {json.dumps(value, ensure_ascii=False)}"


def merge_preserved_translations(
    *,
    checkout: Path,
    tooling_root: Path,
    config: TranslationRepositoryConfig,
    version: str,
    preserved_tree: Path,
    merged_tree: Path,
) -> None:
    """Merge exact-match translations from a preserved tree into a fresh tree."""

    paths = version_paths(config, version)
    fresh_tree = checkout / paths.translation_tree_dir
    _run_tool(
        tooling_root,
        "src/translation_tree.py",
        "merge",
        "--old-tree",
        preserved_tree,
        "--new-tree",
        fresh_tree,
        "--output",
        merged_tree,
        "--source-lang",
        config.translation.source_language,
        "--target-lang",
        config.translation.target_language,
    )
    replace_tree(merged_tree, fresh_tree)


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
        handle.write(f"refreshed_branches={' '.join(result.refreshed_branches)}\n")
        handle.write(f"config_changed={str(result.config_changed).lower()}\n")


def print_summary(result: SyncResult) -> None:
    """Print a concise human-readable sync summary."""

    print("INFO: translation version sync complete")
    print(f"INFO: previous latest version: {result.previous_latest_version}")
    print(f"INFO: current latest version: {result.current_latest_version}")
    print(f"INFO: added versions: {', '.join(result.added_versions) or '(none)'}")
    print(f"INFO: created branches: {', '.join(result.created_branches) or '(none)'}")
    print(f"INFO: refreshed branches: {', '.join(result.refreshed_branches) or '(none)'}")
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


def replace_once(text: str, old: str, new: str) -> str:
    """Replace exactly one occurrence in generated workflow templates."""

    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one workflow template occurrence of {old!r}, got {count}"
        )
    return text.replace(old, new, 1)


def replace_count(text: str, old: str, new: str, *, expected_count: int) -> str:
    """Replace a known repeated marker in generated workflow templates."""

    count = text.count(old)
    if count != expected_count:
        raise SystemExit(
            f"Expected {expected_count} workflow template occurrences of {old!r}, got {count}"
        )
    return text.replace(old, new)


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


def staged_changed_paths(repo: Path) -> list[str]:
    """Return staged paths relative to ``repo``."""

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


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
