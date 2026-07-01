#!/usr/bin/env python3
"""Publish a generated translated document template into a target repository.

This is intentionally a manual helper.  Translation CI can build and validate
artifacts, but publishing to a public downstream repository should be an
explicit operator action.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from dsw_document_template_tool.translation_migration import (  # noqa: E402
    TranslationRepositoryConfig,
    load_translation_repository_config,
    version_branch,
    version_paths,
)
from dsw_document_template_tool.translation_tree import sync_translation_tree  # noqa: E402

# Keep public sync branches close to upstream template source. The transform
# workspace still keeps these files for audit/debug, but they are not part of
# the public handoff repository.
PUBLIC_HANDOFF_EXCLUDED_ROOTS = frozenset({".transform", "UPSTREAM-README.md"})


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=cwd, check=check, capture=capture)


def normalize_repository_location(value: str) -> str:
    local_path = Path(value).expanduser()
    if local_path.exists():
        return str(local_path.resolve())
    if "://" in value or value.startswith("git@"):
        return value
    if "/" in value and not value.endswith(".git"):
        return f"https://github.com/{value}.git"
    return value


def git_ref_exists(repo: Path, ref: str) -> bool:
    result = git(["rev-parse", "--verify", "--quiet", ref], cwd=repo, check=False)
    return result.returncode == 0


def git_remote_exists(repo: Path, name: str) -> bool:
    result = git(["remote", "get-url", name], cwd=repo, check=False, capture=True)
    return result.returncode == 0


def ensure_clean_worktree(repo: Path) -> None:
    status = git(["status", "--porcelain"], cwd=repo, capture=True).stdout.strip()
    if status:
        raise SystemExit(f"Target repository has uncommitted changes:\n{status}")


def checkout_branch(repo: Path, branch: str, base_branch: str, *, detach: bool = False) -> None:
    has_origin = git_remote_exists(repo, "origin")
    if has_origin:
        git(["fetch", "origin", "--prune"], cwd=repo)

    start_ref = publish_start_ref(
        repo=repo,
        branch=branch,
        base_branch=base_branch,
        has_origin=has_origin,
        detach=detach,
    )
    if start_ref:
        checkout_ref(repo, branch, start_ref, detach=detach)
    else:
        raise SystemExit(f"Cannot create {branch!r}: base branch {base_branch!r} was not found")

    ensure_clean_worktree(repo)


def publish_start_ref(
    *,
    repo: Path,
    branch: str,
    base_branch: str,
    has_origin: bool,
    detach: bool,
) -> str | None:
    """Return the safest start ref for publishing.

    Local publishing should preserve an existing local branch. Push publishing
    starts from the remote branch when available because the resulting commit is
    pushed back to that remote ref.
    """

    local_branch = git_ref_exists(repo, f"refs/heads/{branch}")
    remote_branch = has_origin and git_ref_exists(repo, f"refs/remotes/origin/{branch}")
    local_base = git_ref_exists(repo, f"refs/heads/{base_branch}")
    remote_base = has_origin and git_ref_exists(repo, f"refs/remotes/origin/{base_branch}")

    if detach:
        if remote_branch:
            return f"origin/{branch}"
        if local_branch:
            return branch
        if remote_base:
            return f"origin/{base_branch}"
        if local_base:
            return base_branch
        return None
    if local_branch:
        return branch
    if remote_branch:
        return f"origin/{branch}"
    if remote_base:
        return f"origin/{base_branch}"
    if local_base:
        return base_branch
    return None


def checkout_ref(repo: Path, branch: str, start_ref: str, *, detach: bool) -> None:
    """Check out a publishing start point.

    Push publishes the generated commit directly to ``refs/heads/<branch>``, so
    a detached checkout avoids local branch/worktree collisions. Local-only runs
    keep a named branch because it is easier for operators to inspect.
    """

    if detach:
        git(["checkout", "--detach", start_ref], cwd=repo)
        return
    if start_ref == branch:
        git(["checkout", branch], cwd=repo)
        return
    git(["checkout", "-B", branch, start_ref], cwd=repo)


def clear_repository_content(repo: Path) -> None:
    for child in repo.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_template_source(source_dir: Path, target_repo: Path) -> None:
    for child in source_dir.iterdir():
        if child.name in PUBLIC_HANDOFF_EXCLUDED_ROOTS:
            continue
        target = target_repo / child.name
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def has_changes(repo: Path) -> bool:
    return bool(git(["status", "--porcelain"], cwd=repo, capture=True).stdout.strip())


def commit_changes(repo: Path, message: str) -> None:
    git(["config", "user.name", "document-template-publisher"], cwd=repo)
    git(["config", "user.email", "document-template-publisher@example.invalid"], cwd=repo)
    git(["add", "-A"], cwd=repo)
    git(["commit", "-m", message], cwd=repo)


def clone_or_use_target_repo(target_repo: str, temp_root: Path) -> Path:
    location = normalize_repository_location(target_repo)
    local_path = Path(location)
    if local_path.exists():
        return local_path.resolve()

    checkout = temp_root / "publish-target"
    run(["git", "clone", location, str(checkout)])
    return checkout


def source_from_translation_repo(
    translation_repo: Path,
    version: str,
    temp_root: Path,
    config_name: str,
) -> tuple[Path, str | None, str, Path]:
    config = load_translation_repository_config(translation_repo / config_name)
    branch = version_branch(config, version)
    checkout = temp_root / "translation-source"

    git(["fetch", "origin", "--prune"], cwd=translation_repo)
    git(["worktree", "add", "--detach", str(checkout), f"origin/{branch}"], cwd=translation_repo)

    paths = version_paths(config, version)
    source_dir = checkout / paths.translated_template_dir
    if not source_dir.is_dir():
        source_dir = synthesize_translated_template_source(
            checkout=checkout,
            config=config,
            version=version,
            temp_root=temp_root,
        )
    target_repo = config.publish.target_repository
    target_branch = f"{config.publish.branch_prefix}{version}"
    return source_dir, target_repo, target_branch, checkout


def synthesize_translated_template_source(
    *,
    checkout: Path,
    config: TranslationRepositoryConfig,
    version: str,
    temp_root: Path,
) -> Path:
    paths = version_paths(config, version)
    output_dir = temp_root / "translated-template-source" / version
    sync_translation_tree(
        tree_dir=checkout / paths.translation_tree_dir,
        source_dir=checkout / paths.expanded_template_dir,
        output_dir=output_dir,
        source_lang=config.translation.source_language,
        target_lang=config.translation.target_language,
        template_organization_id=config.translation.translated_template_organization_id,
        template_id=config.translation.translated_template_id,
        template_name=config.translation.translated_template_name,
        template_version=paths.version_number,
        public_readme_path=checkout / config.public_readme.path,
    )
    return output_dir


def validate_source_dir(source_dir: Path) -> None:
    if not source_dir.is_dir():
        raise SystemExit(f"Translated template directory does not exist: {source_dir}")
    if not (source_dir / "template.json").is_file():
        raise SystemExit(f"Translated template directory lacks template.json: {source_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--source-dir",
        type=Path,
        help="Existing translated template source directory to publish.",
    )
    source.add_argument(
        "--translation-repo",
        type=Path,
        help=(
            "Translation repository checkout; the requested version branch is "
            "read via a temporary worktree."
        ),
    )
    parser.add_argument("--version", help="Version tag such as v1.30.1.")
    parser.add_argument(
        "--translation-config",
        default="translation-config.yml",
        help="Config file name inside --translation-repo.",
    )
    parser.add_argument(
        "--target-repo",
        help=(
            "Target repository path, clone URL, or GitHub owner/name. Defaults "
            "to translation-config.yml publish.target_repository."
        ),
    )
    parser.add_argument(
        "--target-branch",
        help="Target branch. Defaults to translation-config.yml publish.branch_prefix + version.",
    )
    parser.add_argument("--base-branch", default="main")
    parser.add_argument("--message", help="Commit message.")
    parser.add_argument(
        "--push",
        action="store_true",
        help=(
            "Push the target branch after committing. Without this, only the "
            "local target checkout is updated."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="dsw-template-publish-") as temp_name:
        temp_root = Path(temp_name)
        translation_worktree: Path | None = None

        try:
            config_target_repo: str | None = None
            config_target_branch: str | None = None
            if args.translation_repo:
                if not args.version:
                    raise SystemExit("--version is required with --translation-repo")
                (
                    source_dir,
                    config_target_repo,
                    config_target_branch,
                    translation_worktree,
                ) = source_from_translation_repo(
                    args.translation_repo.resolve(),
                    args.version,
                    temp_root,
                    args.translation_config,
                )
            else:
                source_dir = args.source_dir.resolve()

            target_repo_arg = args.target_repo or config_target_repo
            target_branch = args.target_branch or config_target_branch
            if not target_repo_arg:
                raise SystemExit(
                    "--target-repo is required when no publish target exists in config"
                )
            if not target_branch:
                raise SystemExit(
                    "--target-branch is required when no version/config default is available"
                )

            validate_source_dir(source_dir)
            target_repo = clone_or_use_target_repo(target_repo_arg, temp_root)
            checkout_branch(target_repo, target_branch, args.base_branch, detach=args.push)
            clear_repository_content(target_repo)
            copy_template_source(source_dir, target_repo)

            if not has_changes(target_repo):
                print(f"{target_branch} is already up to date.")
                return 0

            version_suffix = f" {args.version}" if args.version else ""
            message = args.message or f"chore: publish translated template{version_suffix}"
            commit_changes(target_repo, message)

            if args.push:
                if not git_remote_exists(target_repo, "origin"):
                    raise SystemExit(
                        "--push requires the target repository to have an origin remote"
                    )
                git(["push", "origin", f"HEAD:refs/heads/{target_branch}"], cwd=target_repo)
                print(f"Pushed translated template to {target_repo_arg}#{target_branch}.")
            else:
                print(f"Updated local target checkout {target_repo} on {target_branch}.")
            return 0
        finally:
            if args.translation_repo and translation_worktree is not None:
                git(
                    ["worktree", "remove", "--force", str(translation_worktree)],
                    cwd=args.translation_repo.resolve(),
                    check=False,
                )


if __name__ == "__main__":
    raise SystemExit(main())
