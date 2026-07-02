#!/usr/bin/env python3
"""Import safe Weblate review-branch edits into a translation branch."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from _weblate_xliff_merge import XliffMergeReport, merge_weblate_xliff_targets


@dataclass(frozen=True)
class ReconcileResult:
    """Result of one Weblate review-branch reconciliation."""

    action: str
    changed: bool
    review_revision: str | None
    target_revision: str


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Safely import non-conflicting Weblate XLIFF edits into the checked-out "
            "translation/v* branch before normal validation continues."
        ),
    )
    parser.add_argument("--repo", required=True, help="Checked-out translation repository.")
    parser.add_argument("--tooling-root", required=True, help="Checked-out tooling repo root.")
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--weblate-branch", required=True)
    parser.add_argument("--translation-tree-dir", required=True)
    parser.add_argument("--weblate-xliff", required=True)
    parser.add_argument("--source-lang", required=True)
    parser.add_argument("--target-lang", required=True)
    parser.add_argument(
        "--commit-message",
        default="chore(sync): reconcile Weblate translations",
    )
    parser.add_argument("--github-output")
    return parser


def main() -> None:
    """Run Weblate review-branch reconciliation."""

    args = build_argument_parser().parse_args()
    result = reconcile_weblate_review_branch(
        repo=Path(args.repo).resolve(),
        tooling_root=Path(args.tooling_root).resolve(),
        target_branch=args.target_branch,
        weblate_branch=args.weblate_branch,
        translation_tree_dir=Path(args.translation_tree_dir),
        weblate_xliff=Path(args.weblate_xliff),
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        commit_message=args.commit_message,
    )
    write_github_output(
        args.github_output,
        {
            "action": result.action,
            "changed": "true" if result.changed else "false",
            "review_revision": result.review_revision or "",
        },
    )
    print(
        "INFO: Weblate reconciliation "
        f"{result.action}: changed={result.changed} "
        f"review={result.review_revision or '<none>'} "
        f"target={result.target_revision}"
    )


def reconcile_weblate_review_branch(
    *,
    repo: Path,
    tooling_root: Path,
    target_branch: str,
    weblate_branch: str,
    translation_tree_dir: Path,
    weblate_xliff: Path,
    source_lang: str,
    target_lang: str,
    commit_message: str,
) -> ReconcileResult:
    """Import safe review-branch edits into the checked-out target branch."""

    ensure_git_identity(repo)
    ensure_clean_worktree(repo)
    ensure_expected_target_branch(repo, target_branch)

    target_revision = capture(["git", "rev-parse", "HEAD"], cwd=repo).strip()
    review_revision = remote_branch_revision(repo, weblate_branch)
    if review_revision is None:
        return ReconcileResult(
            action="missing-review-branch",
            changed=False,
            review_revision=None,
            target_revision=target_revision,
        )

    remote_ref = fetch_remote_branch(repo, weblate_branch)
    if review_revision == target_revision or is_ancestor(repo, review_revision, "HEAD"):
        return ReconcileResult(
            action="already-contained",
            changed=False,
            review_revision=None,
            target_revision=target_revision,
        )

    with tempfile.TemporaryDirectory(prefix="weblate-reconcile-") as temp_raw:
        temp_root = Path(temp_raw)
        base_xliff = temp_root / "base.xlf"
        merged_xliff = temp_root / "safe-import.xlf"
        review_xliff = temp_root / "review.xlf"

        copy_git_file(
            repo=repo,
            revision=remote_ref,
            relative_path=weblate_xliff,
            output_path=review_xliff,
            required=True,
        )
        merge_base = capture(["git", "merge-base", "HEAD", remote_ref], cwd=repo).strip()
        copy_git_file(
            repo=repo,
            revision=merge_base,
            relative_path=weblate_xliff,
            output_path=base_xliff,
            required=False,
        )

        merge_report = merge_weblate_xliff_targets(
            current_xliff=repo / weblate_xliff,
            review_xliff=review_xliff,
            base_xliff=base_xliff if base_xliff.is_file() else None,
            output_xliff=merged_xliff,
        )
        log_merge_report(merge_report)

        target_changed = False
        if merge_report.changed:
            translation_tree_cli = tooling_root / "src" / "translation_tree.py"
            python = tooling_root / ".venv" / "bin" / "python"
            run(
                [
                    python,
                    translation_tree_cli,
                    "import-xliff",
                    "--tree",
                    repo / translation_tree_dir,
                    "--xliff",
                    merged_xliff,
                    "--source-lang",
                    source_lang,
                    "--target-lang",
                    target_lang,
                ],
            )
            run(
                [
                    python,
                    translation_tree_cli,
                    "export-xliff",
                    "--tree",
                    repo / translation_tree_dir,
                    "--output",
                    repo / weblate_xliff,
                    "--source-lang",
                    source_lang,
                    "--target-lang",
                    target_lang,
                ],
            )
            target_changed = commit_target_changes(
                repo=repo,
                target_branch=target_branch,
                commit_message=commit_message,
                paths=(
                    translation_tree_dir / ".translation-tree" / "manifest.json",
                    translation_tree_dir / "outline.md",
                    translation_tree_dir / "tree",
                    weblate_xliff,
                ),
            )

    return ReconcileResult(
        action="reconciled-review-branch" if target_changed else "review-branch-had-no-safe-edits",
        changed=target_changed,
        review_revision=review_revision,
        target_revision=capture(["git", "rev-parse", "HEAD"], cwd=repo).strip(),
    )


def log_merge_report(report: XliffMergeReport) -> None:
    """Print a compact merge summary for CI logs."""

    print(
        "INFO: Weblate XLIFF merge "
        f"applied={report.applied_units} "
        f"conflicted={report.conflicted_units} "
        f"source_mismatch={report.source_mismatch_units} "
        f"missing_review={report.missing_review_units}"
    )


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
        raise SystemExit("Refusing to reconcile Weblate branch in a dirty checkout:\n" + status)


def ensure_expected_target_branch(repo: Path, target_branch: str) -> None:
    """Ensure the checkout is the target branch the workflow claims to sync."""

    current_branch = capture(["git", "branch", "--show-current"], cwd=repo).strip()
    if current_branch and current_branch != target_branch:
        raise SystemExit(
            f"Refusing to reconcile Weblate branch from {current_branch}; expected {target_branch}."
        )


def remote_branch_revision(repo: Path, branch: str) -> str | None:
    """Return the remote branch revision, or ``None`` when it does not exist."""

    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"Could not query origin/{branch}.")
    line = result.stdout.strip()
    if not line:
        return None
    return line.split()[0]


def fetch_remote_branch(repo: Path, branch: str) -> str:
    """Fetch a remote branch into refs/remotes/origin and return that ref."""

    remote_ref = f"refs/remotes/origin/{branch}"
    run(["git", "fetch", "origin", f"{branch}:{remote_ref}"], cwd=repo)
    return remote_ref


def copy_git_file(
    *,
    repo: Path,
    revision: str,
    relative_path: Path,
    output_path: Path,
    required: bool,
) -> bool:
    """Copy one file from Git history into ``output_path``."""

    result = subprocess.run(
        ["git", "show", f"{revision}:{relative_path.as_posix()}"],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        if required:
            raise SystemExit(
                f"Could not read {relative_path.as_posix()} from {revision}: "
                f"{result.stderr.strip()}"
            )
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.stdout, encoding="utf-8")
    return True


def commit_target_changes(
    *,
    repo: Path,
    target_branch: str,
    commit_message: str,
    paths: tuple[Path, ...],
) -> bool:
    """Commit and push reconciled translation inputs."""

    run(["git", "add", *[path.as_posix() for path in paths]], cwd=repo)
    if not has_staged_changes(repo):
        print("INFO: Weblate reconciliation produced no target-branch changes.")
        return False
    run(["git", "commit", "-m", commit_message], cwd=repo)
    run(["git", "push", "origin", f"HEAD:refs/heads/{target_branch}"], cwd=repo)
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


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    """Return whether ``ancestor`` is reachable from ``descendant``."""

    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo,
            check=False,
        ).returncode
        == 0
    )


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    """Write GitHub Actions step outputs when requested."""

    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


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
