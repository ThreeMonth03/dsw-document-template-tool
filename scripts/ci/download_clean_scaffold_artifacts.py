#!/usr/bin/env python3
"""Download clean upstream scaffold artifacts from a tooling workflow run."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dsw_document_template_tool.translation_migration import load_preview_runtimes  # noqa: E402


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="download clean scaffold artifacts from a tooling CI run",
    )
    parser.add_argument("--repo", required=True, help="GitHub repository, e.g. owner/repo.")
    parser.add_argument(
        "--workflow",
        default="",
        help="Workflow file name or workflow id. Required unless --run-id is provided.",
    )
    parser.add_argument(
        "--branch",
        default="master",
        help="Tooling branch to read successful workflow runs from.",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Exact tooling workflow run id to download from.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tooling-artifacts"),
        help="Directory where artifacts should be downloaded.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        dest="artifacts",
        help=(
            "Artifact name to download. May be repeated. Defaults to all configured "
            "clean-upstream-version artifact names from config/dsw-compat.yml."
        ),
    )
    args = parser.parse_args()

    try:
        artifacts = tuple(args.artifacts or default_clean_artifact_names())
        run_id = args.run_id.strip() or latest_successful_run_id(
            repo=args.repo,
            workflow=args.workflow,
            branch=args.branch,
        )
        if not run_id:
            raise RuntimeError("No successful tooling CI run found")

        for artifact in artifacts:
            download_artifact(
                repo=args.repo,
                run_id=run_id,
                artifact=artifact,
                output_dir=args.output_dir,
            )

        workspace_root = args.output_dir / "upstream-workspaces"
        if not workspace_root.is_dir():
            raise RuntimeError(
                f"Downloaded artifacts did not contain {workspace_root.as_posix()}",
            )
        print(
            "Downloaded clean scaffold artifacts from "
            f"{args.repo} run {run_id}: {', '.join(artifacts)}"
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def default_clean_artifact_names() -> list[str]:
    """Return clean scaffold artifact names for all configured preview runtimes."""

    return [
        f"clean-upstream-version-artifacts-metamodel-{runtime.metamodel_key}"
        for runtime in load_preview_runtimes()
    ]


def latest_successful_run_id(*, repo: str, workflow: str, branch: str) -> str:
    """Return the latest successful workflow run database id."""

    if not workflow:
        raise RuntimeError("--workflow is required when --run-id is not provided")

    result = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            workflow,
            "--branch",
            branch,
            "--status",
            "success",
            "--limit",
            "1",
            "--json",
            "databaseId",
            "--jq",
            ".[0].databaseId // empty",
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def download_artifact(
    *,
    repo: str,
    run_id: str,
    artifact: str,
    output_dir: Path,
) -> None:
    """Download one artifact, raising a clear error on failure."""

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{artifact}-") as temp_raw:
        temp_dir = Path(temp_raw)
        artifact_dir = temp_dir / "artifact"
        artifact_dir.mkdir()
        download_artifact_to_directory(
            repo=repo,
            run_id=run_id,
            artifact=artifact,
            output_dir=artifact_dir,
        )
        merge_artifact_tree(artifact_dir, output_dir)


def download_artifact_to_directory(
    *,
    repo: str,
    run_id: str,
    artifact: str,
    output_dir: Path,
) -> None:
    """Download one artifact into an empty directory."""

    result = subprocess.run(
        [
            "gh",
            "run",
            "download",
            run_id,
            "--repo",
            repo,
            "--name",
            artifact,
            "--dir",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Clean scaffold artifact download failed for {artifact}: {detail}")


def merge_artifact_tree(source: Path, destination: Path) -> None:
    """Merge one downloaded artifact tree into the shared output directory."""

    for source_path in sorted(source.rglob("*")):
        relative_path = source_path.relative_to(source)
        destination_path = destination / relative_path
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if not destination_path.exists():
            shutil.copy2(source_path, destination_path)
            continue
        if destination_path.is_dir():
            raise RuntimeError(f"Cannot merge file over directory: {relative_path.as_posix()}")
        if should_replace_duplicate_artifact_file(relative_path):
            shutil.copy2(source_path, destination_path)
            continue
        if source_path.read_bytes() == destination_path.read_bytes():
            continue
        raise RuntimeError(
            f"Artifact download produced conflicting files at {relative_path.as_posix()}"
        )


def should_replace_duplicate_artifact_file(relative_path: Path) -> bool:
    """Return whether duplicate artifact files may be replaced safely."""

    return relative_path.parts[:1] == ("compat-ledger",)


if __name__ == "__main__":
    main()
