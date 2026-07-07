#!/usr/bin/env python3
"""Publish clean scaffold GitHub Release assets for built upstream artifacts."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from stage_release_assets import (  # noqa: E402
    AssetSpec,
    reset_output_dir,
    stage_directory_archive,
    stage_file,
    write_checksums,
    write_release_notes,
)


def main() -> None:
    """Publish or dry-run clean scaffold release assets."""

    args = parse_args()
    packages = find_packages(
        outputs_root=args.outputs_root,
        source_template_id=args.source_template_id,
        translation_locale=args.translation_locale,
    )
    if not packages:
        print("No clean scaffold packages were produced for this runtime.")
        return

    repository = args.repository or os.environ.get("GITHUB_REPOSITORY", "")
    commit_sha = args.commit_sha or os.environ.get("GITHUB_SHA", "")
    if not repository and not args.dry_run:
        raise SystemExit("--repository is required when GITHUB_REPOSITORY is not set")
    if not commit_sha and not args.dry_run:
        raise SystemExit("--commit-sha is required when GITHUB_SHA is not set")
    repository = repository or "unknown/repository"
    package_root = args.outputs_root / "document-templates" / args.source_template_id

    for package in packages:
        version_tag = version_tag_from_path(package, package_root=package_root)
        release = CleanScaffoldRelease(
            version_tag=version_tag,
            package=package,
            outputs_root=args.outputs_root,
            release_root=args.release_root,
            repository=repository,
            run_id=args.run_id or os.environ.get("GITHUB_RUN_ID", ""),
            commit_sha=commit_sha,
            source_template_id=args.source_template_id,
            translation_locale=args.translation_locale,
        )
        stage_clean_scaffold_release(release)
        if args.dry_run:
            print(f"INFO: dry-run staged {release.release_tag} in {release.release_dir}")
            continue
        publish_release(release)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-sha", help="Commit SHA used in release notes and target.")
    parser.add_argument("--dry-run", action="store_true", help="Stage assets without using gh.")
    parser.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--release-root", type=Path, default=Path("outputs/release-assets/clean-scaffold")
    )
    parser.add_argument("--repository", help="GitHub repository, for example owner/name.")
    parser.add_argument("--run-id", help="GitHub Actions run id for release notes.")
    parser.add_argument("--source-template-id", default="dsw-science-europe")
    parser.add_argument("--translation-locale", default="zh-Hant")
    return parser.parse_args()


class CleanScaffoldRelease:
    """Paths and metadata for one clean scaffold release."""

    def __init__(
        self,
        *,
        version_tag: str,
        package: Path,
        outputs_root: Path,
        release_root: Path,
        repository: str,
        run_id: str,
        commit_sha: str,
        source_template_id: str,
        translation_locale: str,
    ) -> None:
        self.version_tag = version_tag
        self.package = package
        self.repository = repository
        self.run_id = run_id
        self.commit_sha = commit_sha
        self.source_template_id = source_template_id
        self.translation_locale = translation_locale
        self.release_tag = f"clean-scaffold-{source_template_id}-{version_tag}"
        self.release_title = f"Clean {source_template_id} scaffold {version_tag}"
        self.release_dir = release_root / version_tag
        self.workspace_dir = outputs_root / "upstream-workspaces" / source_template_id / version_tag
        self.preview_dir = (
            outputs_root
            / "project-render"
            / source_template_id
            / version_tag
            / translation_locale
            / "scaffold"
        )


def find_packages(
    *,
    outputs_root: Path,
    source_template_id: str,
    translation_locale: str,
) -> list[Path]:
    """Return clean scaffold package files produced by the current runtime."""

    package_root = outputs_root / "document-templates" / source_template_id
    return sorted(package_root.glob(f"v*/{translation_locale}/scaffold/*.zip"))


def version_tag_from_path(path: Path, *, package_root: Path | None = None) -> str:
    """Extract the vX.Y.Z package-root path component from an artifact path."""

    if package_root is not None:
        try:
            version_tag = path.relative_to(package_root).parts[0]
        except (IndexError, ValueError) as exc:
            raise SystemExit(f"Could not infer version tag from package path: {path}") from exc
        if is_version_tag(version_tag):
            return version_tag
        raise SystemExit(f"Could not infer version tag from package path: {path}")

    for part in path.parts:
        if is_version_tag(part):
            return part
    raise SystemExit(f"Could not infer version tag from package path: {path}")


def is_version_tag(value: str) -> bool:
    """Return whether a path component looks like vX.Y.Z."""

    parts = value.removeprefix("v").split(".")
    return value.startswith("v") and len(parts) == 3 and all(part.isdigit() for part in parts)


def stage_clean_scaffold_release(release: CleanScaffoldRelease) -> None:
    """Stage package, workspace archive, preview archive, checksums, and notes."""

    reset_output_dir(release.release_dir)
    staged_files = [
        stage_file(
            AssetSpec(source=release.package, name=release.package.name), release.release_dir
        )
    ]
    workspace_asset = f"clean-workspace-{release.source_template_id}-{release.version_tag}.zip"
    staged_files.append(
        stage_directory_archive(
            AssetSpec(source=release.workspace_dir, name=workspace_asset),
            release.release_dir,
        )
    )
    preview_asset = f"clean-preview-{release.source_template_id}-{release.version_tag}.zip"
    staged_preview = stage_directory_archive(
        AssetSpec(source=release.preview_dir, name=preview_asset, optional=True),
        release.release_dir,
    )
    if staged_preview is not None:
        staged_files.append(staged_preview)

    checksums_path = release.release_dir / "SHA256SUMS"
    write_checksums(checksums_path, staged_files)
    notes_path = release.release_dir / "release-notes.md"
    write_release_notes(
        notes_path,
        title=release.release_title,
        body=[
            (
                f"Generated by {release.repository} run {release.run_id} "
                f"from commit {release.commit_sha}."
            ),
            (
                "These are clean scaffolds for downstream translation maintenance, "
                "not finished public translations."
            ),
        ],
        staged_files=[*staged_files, checksums_path],
        checksums_file=checksums_path.name,
    )


def publish_release(release: CleanScaffoldRelease) -> None:
    """Create/update one prerelease and upload staged assets."""

    notes_file = release.release_dir / "release-notes.md"
    if release_exists(release):
        sync_release_tag(release)
        run(
            [
                "gh",
                "release",
                "edit",
                release.release_tag,
                "--repo",
                release.repository,
                "--title",
                release.release_title,
                "--notes-file",
                str(notes_file),
                "--target",
                release.commit_sha,
                "--prerelease",
            ]
        )
    else:
        run(
            [
                "gh",
                "release",
                "create",
                release.release_tag,
                "--repo",
                release.repository,
                "--title",
                release.release_title,
                "--notes-file",
                str(notes_file),
                "--prerelease",
                "--latest=false",
                "--target",
                release.commit_sha,
            ]
        )

    run(
        [
            "gh",
            "release",
            "upload",
            release.release_tag,
            *[str(path) for path in sorted(release.release_dir.iterdir())],
            "--repo",
            release.repository,
            "--clobber",
        ]
    )


def sync_release_tag(release: CleanScaffoldRelease) -> None:
    """Point the mutable release tag at the commit that produced the assets."""

    ref_name = f"tags/{release.release_tag}"
    if tag_exists(release, ref_name):
        run(
            [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{release.repository}/git/refs/{ref_name}",
                "-f",
                f"sha={release.commit_sha}",
                "-F",
                "force=true",
            ]
        )
        return

    run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{release.repository}/git/refs",
            "-f",
            f"ref=refs/{ref_name}",
            "-f",
            f"sha={release.commit_sha}",
        ]
    )


def tag_exists(release: CleanScaffoldRelease, ref_name: str) -> bool:
    """Return whether the release tag exists."""

    return (
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{release.repository}/git/ref/{ref_name}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def release_exists(release: CleanScaffoldRelease) -> bool:
    """Return whether the GitHub release exists."""

    return (
        subprocess.run(
            [
                "gh",
                "release",
                "view",
                release.release_tag,
                "--repo",
                release.repository,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def run(args: list[str]) -> None:
    """Run one command."""

    subprocess.run(args, check=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
