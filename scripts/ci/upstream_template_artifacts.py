#!/usr/bin/env python3
"""Build and preview clean upstream Science Europe scaffold artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from cli_commands import (  # noqa: E402
    RENDER_PROJECT_COMMAND,
    TRANSFORM_TEMPLATE_COMMAND,
    TRANSLATION_TREE_COMMAND,
    tool_command,
)
from resolve_upstream_refs import normalize_git_remote, resolve_refs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_tags = subparsers.add_parser("list-tags", help="List upstream version tags.")
    list_tags.add_argument("--remote", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch one upstream ref into a cache.")
    fetch.add_argument("--remote", required=True)
    fetch.add_argument("--ref", required=True)
    fetch.add_argument("--cache", type=Path, required=True)

    smoke = subparsers.add_parser(
        "test-tags",
        help="Smoke-test upstream refs with transform/export/sync/package.",
    )
    add_common_build_args(smoke)
    smoke.add_argument("--root", type=Path, required=True)
    smoke.add_argument("--test-metamodel-version", default="")

    build = subparsers.add_parser(
        "build-artifacts",
        help="Build clean workspaces, translation trees, and scaffold packages.",
    )
    add_common_build_args(build)
    build.add_argument("--artifact-cache-root", type=Path, required=True)
    build.add_argument("--artifact-metamodel-version", default="")
    build.add_argument("--artifact-workspace-root", type=Path, required=True)
    build.add_argument("--translation-locale", required=True)
    build.add_argument("--scaffold-template-id", required=True)
    build.add_argument("--scaffold-template-name", required=True)

    previews = subparsers.add_parser(
        "render-previews",
        help="Render clean scaffold demo PDFs for already-built artifacts.",
    )
    previews.add_argument("--format-uuid", required=True)
    previews.add_argument("--project-ref", required=True)
    previews.add_argument("--preview-metamodel-version", required=True)
    previews.add_argument("--python", default=sys.executable)
    previews.add_argument("--source-template-id", required=True)
    previews.add_argument("--tdk-executable", required=True)
    previews.add_argument("--translated-template-organization-id", required=True)
    previews.add_argument("--translation-locale", required=True)
    previews.add_argument("--scaffold-template-id", required=True)

    args = parser.parse_args()
    if hasattr(args, "remote"):
        args.remote = normalize_git_remote(args.remote)
    if args.command == "list-tags":
        list_upstream_tags(args.remote)
    elif args.command == "fetch":
        fetch_upstream_template(remote=args.remote, ref=args.ref, cache=args.cache)
    elif args.command == "test-tags":
        smoke_test_upstream_tags(args)
    elif args.command == "build-artifacts":
        build_upstream_artifacts(args)
    elif args.command == "render-previews":
        render_upstream_artifact_previews(args)


def add_common_build_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--remote", required=True)
    parser.add_argument("--refs", nargs="+", required=True)
    parser.add_argument("--source-template-id", required=True)
    parser.add_argument("--tdk-executable", required=True)
    parser.add_argument("--translated-template-id", required=True)
    parser.add_argument("--translated-template-name", required=True)
    parser.add_argument("--translated-template-organization-id", required=True)


def list_upstream_tags(remote: str) -> None:
    tags = [
        line.split("refs/tags/", 1)[1]
        for line in git_stdout(None, "ls-remote", "--tags", "--refs", remote, "v*").splitlines()
        if "refs/tags/" in line
    ]
    print("\n".join(sorted(tags, key=version_sort_key)))


def fetch_upstream_template(*, remote: str, ref: str, cache: Path) -> str:
    cache.mkdir(parents=True, exist_ok=True)
    if not (cache / ".git").is_dir():
        print(f"INFO: Initializing upstream template cache at {cache}")
        run(["git", "-C", str(cache), "init"])
        run(["git", "-C", str(cache), "remote", "add", "origin", remote])
    else:
        print(f"INFO: Updating upstream template cache at {cache}")
        run(["git", "-C", str(cache), "remote", "set-url", "origin", remote])

    run(
        [
            "git",
            "-C",
            str(cache),
            "fetch",
            "--prune",
            "--tags",
            "origin",
            "+refs/heads/*:refs/remotes/origin/*",
        ]
    )
    resolved_ref = resolve_single_ref(cache, ref)
    checkout_ref = (
        f"origin/{resolved_ref}"
        if git_ref_exists(cache, f"origin/{resolved_ref}")
        else resolved_ref
    )
    run(["git", "-C", str(cache), "checkout", "--force", "--detach", checkout_ref])
    short_sha = git_stdout(cache, "rev-parse", "--short", "HEAD").strip()
    print(f"INFO: Upstream template ref {ref} resolved to {resolved_ref} ({short_sha})")
    return resolved_ref


def smoke_test_upstream_tags(args: argparse.Namespace) -> None:
    refs = resolve_refs(remote=args.remote, refs=args.refs)
    print("INFO: Smoke-testing upstream refs: " + " ".join(refs))
    for ref in refs:
        case_root = args.root / safe_ref_name(ref)
        clean_allowed_root(case_root, allowed_prefixes=(".cache", "/tmp", "/var/tmp"))
        cache_dir = case_root / "upstream"
        expanded_dir = case_root / "expanded"
        tree_dir = case_root / "translation-tree"
        output_dir = case_root / "output"
        package_path = case_root / "output.zip"

        print(f"INFO: [{ref}] fetching upstream")
        fetch_upstream_template(remote=args.remote, ref=ref, cache=cache_dir)
        version, metamodel_version = template_version_and_metamodel(cache_dir)
        version_tag = f"v{version}"
        if args.test_metamodel_version and metamodel_version != args.test_metamodel_version:
            print(
                f"INFO: [{ref}] skipping smoke test for version {version_tag} because "
                f"metamodel {metamodel_version} is not handled by test metamodel "
                f"{args.test_metamodel_version}"
            )
            continue

        print(f"INFO: [{ref}] transform/export/sync/package version {version}")
        expand_template(source=cache_dir, output=expanded_dir)
        export_translation_tree(source=expanded_dir, output=tree_dir)
        sync_translation_tree(
            tree=tree_dir,
            source=expanded_dir,
            output=output_dir,
            organization_id=args.translated_template_organization_id,
            template_id=f"{args.translated_template_id}-smoke",
            template_name=f"{args.translated_template_name} Smoke Test",
            template_version=version,
        )
        audit_output(source=expanded_dir, output=output_dir)
        run([args.tdk_executable, "verify", str(output_dir)])
        run(
            [
                args.tdk_executable,
                "package",
                str(output_dir),
                "--output",
                str(package_path),
                "--force",
            ]
        )
        print(f"INFO: [{ref}] passed")


def build_upstream_artifacts(args: argparse.Namespace) -> None:
    refs = resolve_refs(remote=args.remote, refs=args.refs)
    print("INFO: Building clean upstream artifacts for refs: " + " ".join(refs))
    for ref in refs:
        cache_dir = args.artifact_cache_root / safe_ref_name(ref) / "upstream"
        print(f"INFO: [{ref}] fetching upstream")
        fetch_upstream_template(remote=args.remote, ref=ref, cache=cache_dir)
        version, metamodel_version = template_version_and_metamodel(cache_dir)
        version_tag = f"v{version}"
        if args.artifact_metamodel_version and metamodel_version != args.artifact_metamodel_version:
            print(
                f"INFO: [{ref}] skipping version {version_tag} because metamodel "
                f"{metamodel_version} is not handled by artifact metamodel "
                f"{args.artifact_metamodel_version}"
            )
            continue

        workspace_root = args.artifact_workspace_root / version_tag
        workspace_template_name = f"{args.source_template_id}-{version}"
        compact_dir = workspace_root / "compact" / workspace_template_name
        expanded_dir = workspace_root / "expanded" / workspace_template_name
        regression_expanded_dir = workspace_root / "expanded-regression" / workspace_template_name
        tree_dir = workspace_root / "translation" / workspace_template_name
        output_root = (
            Path("outputs")
            / "document-templates"
            / args.source_template_id
            / version_tag
            / args.translation_locale
            / "scaffold"
        )
        output_dir = (
            output_root
            / f"{args.translated_template_organization_id}-{args.scaffold_template_id}-{version}"
        )
        package_name = (
            f"{args.translated_template_organization_id}-"
            f"{args.scaffold_template_id}-{version}.zip"
        )
        package_path = output_root / package_name

        clean_allowed_root(workspace_root, allowed_prefixes=("outputs",))
        clean_allowed_root(output_root, allowed_prefixes=("outputs",))
        compact_dir.parent.mkdir(parents=True, exist_ok=True)
        output_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(cache_dir, compact_dir)
        shutil.rmtree(compact_dir / ".git", ignore_errors=True)
        write_upstream_metadata(
            workspace_root=workspace_root,
            remote=args.remote,
            requested_ref=ref,
            cache_dir=cache_dir,
            source_template_id=args.source_template_id,
            version=version,
        )

        print(f"INFO: [{ref}] transform/export/sync/package version {version}")
        expand_template(source=compact_dir, output=regression_expanded_dir, local_patches=False)
        expand_template(source=compact_dir, output=expanded_dir)
        export_translation_tree(source=expanded_dir, output=tree_dir)
        sync_translation_tree(
            tree=tree_dir,
            source=expanded_dir,
            output=output_dir,
            organization_id=args.translated_template_organization_id,
            template_id=args.scaffold_template_id,
            template_name=args.scaffold_template_name,
            template_version=version,
        )
        audit_output(source=expanded_dir, output=output_dir)
        run([args.tdk_executable, "verify", str(output_dir)])
        run(
            [
                args.tdk_executable,
                "package",
                str(output_dir),
                "--output",
                str(package_path),
                "--force",
            ]
        )
        print(f"INFO: [{ref}] artifact package written to {package_path}")


def render_upstream_artifact_previews(args: argparse.Namespace) -> None:
    artifact_root = Path("outputs") / "document-templates" / args.source_template_id
    template_dirs = sorted(
        path
        for path in artifact_root.glob(
            "v*/"
            f"{args.translation_locale}/"
            "scaffold/"
            f"{args.translated_template_organization_id}-{args.scaffold_template_id}-*"
        )
        if path.is_dir()
    )
    if not template_dirs:
        raise SystemExit(
            "No scaffold template directories found. Run make build-upstream-artifacts first."
        )

    for template_dir in template_dirs:
        version, metamodel_version = template_version_and_metamodel(template_dir)
        version_tag = f"v{version}"
        package_path = package_path_for_template_dir(template_dir)
        if not package_path.is_file():
            raise SystemExit(
                f"Missing scaffold package for {version_tag}: {package_path}. "
                "Run make build-upstream-artifacts first."
            )
        output_path = (
            Path("outputs")
            / "project-render"
            / args.source_template_id
            / version_tag
            / args.translation_locale
            / "scaffold"
            / "test-project.pdf"
        )
        if metamodel_version != args.preview_metamodel_version:
            status_path = output_path.parent / "skipped.json"
            write_preview_status(
                args.python,
                output=status_path,
                status="skipped",
                reason="unsupported_metamodel_version",
                version_tag=version_tag,
                template_metamodel_version=metamodel_version,
                preview_metamodel_version=args.preview_metamodel_version,
            )
            print(
                f"INFO: Skipping scaffold demo for {version_tag}: metamodel "
                f"{metamodel_version} is not supported by preview DSW metamodel "
                f"{args.preview_metamodel_version}"
            )
            continue

        print(f"INFO: Rendering scaffold demo for {version_tag} to {output_path}")
        render_status = run(
            tool_command(
                REPO_ROOT,
                RENDER_PROJECT_COMMAND,
                "--project-ref",
                args.project_ref,
                "--template-package",
                package_path,
                "--format-uuid",
                args.format_uuid,
                "--output",
                output_path,
                "--tdk-executable",
                args.tdk_executable,
            ),
            check=False,
        ).returncode
        if render_status == 0:
            continue

        failure_path = output_path.parent / "failed.json"
        write_preview_status(
            args.python,
            output=failure_path,
            status="failed",
            reason="render_failed",
            version_tag=version_tag,
            template_metamodel_version=metamodel_version,
            preview_metamodel_version=args.preview_metamodel_version,
            exit_code=render_status,
        )
        print(f"WARNING: Scaffold demo failed for {version_tag}; wrote {failure_path}")
        raise SystemExit(render_status)


def resolve_single_ref(repo: Path, requested_ref: str) -> str:
    if requested_ref == "latest":
        tags = [
            tag
            for tag in git_stdout(repo, "tag", "-l", "v*").splitlines()
            if tag.startswith("v") and all(part.isdigit() for part in tag[1:].split("."))
        ]
        if not tags:
            raise SystemExit("Could not resolve upstream template ref 'latest'.")
        return sorted(tags, key=version_sort_key)[-1]
    return requested_ref


def clean_allowed_root(path: Path, *, allowed_prefixes: tuple[str, ...]) -> None:
    path_text = path.as_posix()
    if not any(
        path_text == prefix or path_text.startswith(f"{prefix}/") for prefix in allowed_prefixes
    ):
        raise SystemExit(f"Refusing to clean unsafe path {path}")
    shutil.rmtree(path, ignore_errors=True)


def safe_ref_name(ref: str) -> str:
    safe = "".join(char if char.isalnum() or char in "._-" else "-" for char in ref)
    return safe or "ref"


def template_version_and_metamodel(template_dir: Path) -> tuple[str, str]:
    payload = json.loads((template_dir / "template.json").read_text(encoding="utf-8"))
    return str(payload["version"]), str(payload.get("metamodelVersion", ""))


def package_path_for_template_dir(template_dir: Path) -> Path:
    """Return the sibling package path without treating version dots as suffixes."""
    return template_dir.parent / f"{template_dir.name}.zip"


def write_upstream_metadata(
    *,
    workspace_root: Path,
    remote: str,
    requested_ref: str,
    cache_dir: Path,
    source_template_id: str,
    version: str,
) -> None:
    commit_sha = git_stdout(cache_dir, "rev-parse", "HEAD").strip()
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "upstream.json").write_text(
        json.dumps(
            {
                "repository": remote,
                "requested_ref": requested_ref,
                "commit_sha": commit_sha,
                "template_id": source_template_id,
                "template_version": version,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def expand_template(*, source: Path, output: Path, local_patches: bool = True) -> None:
    args = [
        *tool_command(REPO_ROOT, TRANSFORM_TEMPLATE_COMMAND),
        "expand",
        "--source",
        str(source),
        "--output",
        str(output),
    ]
    if not local_patches:
        args.append("--no-local-patches")
    run(args)


def export_translation_tree(*, source: Path, output: Path) -> None:
    run(
        tool_command(
            REPO_ROOT,
            TRANSLATION_TREE_COMMAND,
            "export",
            "--source",
            source,
            "--output",
            output,
        ),
    )


def sync_translation_tree(
    *,
    tree: Path,
    source: Path,
    output: Path,
    organization_id: str,
    template_id: str,
    template_name: str,
    template_version: str,
) -> None:
    run(
        tool_command(
            REPO_ROOT,
            TRANSLATION_TREE_COMMAND,
            "sync",
            "--tree",
            tree,
            "--source",
            source,
            "--output",
            output,
            "--template-organization-id",
            organization_id,
            "--template-id",
            template_id,
            "--template-name",
            template_name,
            "--template-version",
            template_version,
        ),
    )


def audit_output(*, source: Path, output: Path) -> None:
    run(
        tool_command(
            REPO_ROOT,
            TRANSLATION_TREE_COMMAND,
            "audit-output",
            "--source",
            source,
            "--output",
            output,
        ),
    )


def write_preview_status(
    python: str,
    *,
    output: Path,
    status: str,
    reason: str,
    version_tag: str,
    template_metamodel_version: str,
    preview_metamodel_version: str,
    exit_code: int | None = None,
) -> None:
    args = [
        python,
        "scripts/ci/write_preview_status.py",
        "--output",
        str(output),
        "--status",
        status,
        "--reason",
        reason,
        "--template-version",
        version_tag,
        "--template-metamodel-version",
        template_metamodel_version,
        "--preview-metamodel-version",
        preview_metamodel_version,
    ]
    if exit_code is not None:
        args.extend(["--exit-code", str(exit_code)])
    run(args)


def version_sort_key(value: str) -> tuple[int, ...]:
    version = value[1:] if value.startswith("v") else value
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def git_ref_exists(repo: Path, ref: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", ref],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def git_stdout(repo: Path | None, *args: str) -> str:
    command = ["git", *args] if repo is None else ["git", "-C", str(repo), *args]
    return subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True).stdout


def run(
    args: list[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, env=env)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
