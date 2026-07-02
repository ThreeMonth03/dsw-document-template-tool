#!/usr/bin/env python3
"""Promote Weblate-edited XLIFF from a review branch into a translation branch."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Copy Weblate XLIFF from a weblate/v* branch into a checked-out "
            "translation/v* branch, import it, validate structure, and push."
        ),
    )
    parser.add_argument("--host-root", required=True, help="Checked-out translation repo root.")
    parser.add_argument("--tooling-root", required=True, help="Checked-out tooling repo root.")
    parser.add_argument("--target-branch", required=True, help="Target translation/v* branch.")
    parser.add_argument("--weblate-branch", required=True, help="Source weblate/v* branch.")
    parser.add_argument("--compact-template-dir", required=True)
    parser.add_argument("--expanded-template-dir", required=True)
    parser.add_argument("--translation-tree-dir", required=True)
    parser.add_argument("--weblate-xliff", required=True)
    parser.add_argument("--translated-template-dir", required=True)
    parser.add_argument("--template-organization-id", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--template-name", required=True)
    parser.add_argument("--template-version", required=True)
    parser.add_argument("--public-readme", required=True)
    parser.add_argument("--source-lang", required=True)
    parser.add_argument("--target-lang", required=True)
    parser.add_argument(
        "--commit-message",
        default="chore(sync): import Weblate translations",
        help="Commit message used when promotion changes the target branch.",
    )
    parser.add_argument(
        "--github-output",
        help="Optional GitHub Actions output file used to report changed=true/false.",
    )
    return parser


def main() -> None:
    """Run Weblate XLIFF promotion."""

    args = build_argument_parser().parse_args()
    host_root = Path(args.host_root).resolve()
    tooling_root = Path(args.tooling_root).resolve()
    python = tooling_root / ".venv" / "bin" / "python"
    transform_template = tooling_root / "src" / "transform_template.py"
    translation_tree = tooling_root / "src" / "translation_tree.py"

    ensure_git_identity(host_root)
    ensure_clean_worktree(host_root)
    ensure_checked_out_target_branch(host_root, args.target_branch)
    copy_weblate_xliff(
        host_root=host_root,
        weblate_branch=args.weblate_branch,
        weblate_xliff=Path(args.weblate_xliff),
    )

    expanded_template_dir = host_root / args.expanded_template_dir
    translation_tree_dir = host_root / args.translation_tree_dir
    translated_template_dir = host_root / args.translated_template_dir
    weblate_xliff = host_root / args.weblate_xliff

    with tempfile.TemporaryDirectory(prefix="weblate-promotion-") as temp_raw:
        temp_root = Path(temp_raw)
        fresh_translation_tree = temp_root / "fresh-translation-tree"
        merged_translation_tree = temp_root / "merged-translation-tree"

        run(
            [
                python,
                transform_template,
                "expand",
                "--source",
                host_root / args.compact_template_dir,
                "--output",
                expanded_template_dir,
            ],
        )
        run(
            [
                python,
                translation_tree,
                "export",
                "--source",
                expanded_template_dir,
                "--output",
                fresh_translation_tree,
            ],
        )
        if (translation_tree_dir / ".translation-tree" / "manifest.json").is_file():
            run(
                [
                    python,
                    translation_tree,
                    "merge",
                    "--old-tree",
                    translation_tree_dir,
                    "--new-tree",
                    fresh_translation_tree,
                    "--output",
                    merged_translation_tree,
                    "--source-lang",
                    args.source_lang,
                    "--target-lang",
                    args.target_lang,
                ],
            )
        else:
            shutil.copytree(fresh_translation_tree, merged_translation_tree)

        replace_tree(merged_translation_tree, translation_tree_dir)

    run(
        [
            python,
            translation_tree,
            "import-xliff",
            "--tree",
            translation_tree_dir,
            "--xliff",
            weblate_xliff,
            "--source-lang",
            args.source_lang,
            "--target-lang",
            args.target_lang,
        ],
    )
    run(
        [
            python,
            translation_tree,
            "export-xliff",
            "--tree",
            translation_tree_dir,
            "--output",
            weblate_xliff,
            "--source-lang",
            args.source_lang,
            "--target-lang",
            args.target_lang,
        ],
    )
    run(
        [
            python,
            translation_tree,
            "audit",
            "--tree",
            translation_tree_dir,
            "--source",
            expanded_template_dir,
        ],
    )
    run(
        [
            python,
            translation_tree,
            "sync",
            "--tree",
            translation_tree_dir,
            "--source",
            expanded_template_dir,
            "--output",
            translated_template_dir,
            "--template-organization-id",
            args.template_organization_id,
            "--template-id",
            args.template_id,
            "--template-name",
            args.template_name,
            "--template-version",
            args.template_version,
            "--public-readme",
            host_root / args.public_readme,
        ],
    )
    run(
        [
            python,
            translation_tree,
            "audit-output",
            "--source",
            expanded_template_dir,
            "--output",
            translated_template_dir,
        ],
    )

    changed = commit_and_push(
        host_root=host_root,
        target_branch=args.target_branch,
        commit_message=args.commit_message,
        paths=(
            Path(args.expanded_template_dir),
            Path(args.translation_tree_dir) / ".translation-tree" / "manifest.json",
            Path(args.translation_tree_dir) / "outline.md",
            Path(args.translation_tree_dir) / "tree",
            Path(args.weblate_xliff),
        ),
    )
    write_github_output(args.github_output, {"changed": "true" if changed else "false"})


def ensure_git_identity(repo: Path) -> None:
    """Configure the bot identity used by GitHub Actions commits."""

    run(["git", "config", "user.name", "github-actions[bot]"], cwd=repo)
    run(
        [
            "git",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        cwd=repo,
    )


def ensure_clean_worktree(repo: Path) -> None:
    """Fail before touching a checkout that contains local work."""

    status = capture(["git", "status", "--short"], cwd=repo)
    if status.strip():
        raise SystemExit("Refusing to promote Weblate XLIFF in a dirty checkout:\n" + status)


def ensure_checked_out_target_branch(repo: Path, target_branch: str) -> None:
    """Ensure the checkout is based on the latest target branch."""

    run(["git", "fetch", "origin", target_branch], cwd=repo)
    current_branch = capture(["git", "branch", "--show-current"], cwd=repo).strip()
    if current_branch != target_branch:
        run(["git", "checkout", "-B", target_branch, f"origin/{target_branch}"], cwd=repo)
    else:
        run(["git", "reset", "--hard", f"origin/{target_branch}"], cwd=repo)


def copy_weblate_xliff(
    *,
    host_root: Path,
    weblate_branch: str,
    weblate_xliff: Path,
) -> None:
    """Copy the Weblate XLIFF file from the review branch into the target checkout."""

    remote_ref = f"refs/remotes/origin/{weblate_branch}"
    run(["git", "fetch", "origin", f"{weblate_branch}:{remote_ref}"], cwd=host_root)
    source_spec = f"{remote_ref}:{weblate_xliff.as_posix()}"
    xliff_text = capture(["git", "show", source_spec], cwd=host_root)
    target_path = host_root / weblate_xliff
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(xliff_text, encoding="utf-8")


def commit_and_push(
    *,
    host_root: Path,
    target_branch: str,
    commit_message: str,
    paths: tuple[Path, ...],
) -> bool:
    """Commit promoted translation inputs and push the target branch."""

    run(["git", "add", *[path.as_posix() for path in paths]], cwd=host_root)
    if not has_staged_changes(host_root):
        print("INFO: Weblate promotion produced no target-branch changes.")
        return False

    run(["git", "commit", "-m", commit_message], cwd=host_root)
    run(["git", "push", "origin", f"HEAD:refs/heads/{target_branch}"], cwd=host_root)
    return True


def has_staged_changes(repo: Path) -> bool:
    """Return whether there are staged changes."""

    return (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    """Write GitHub Actions step outputs when requested."""

    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def replace_tree(source: Path, destination: Path) -> None:
    """Replace one directory tree."""

    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def capture(command: list[object], *, cwd: Path) -> str:
    """Run a command and return stdout."""

    result = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def run(command: list[object], *, cwd: Path | None = None) -> None:
    """Run a command with inherited output."""

    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(
            f"ERROR: command failed with exit code {error.returncode}: "
            + " ".join(str(part) for part in error.cmd),
            file=sys.stderr,
        )
        sys.exit(error.returncode)
