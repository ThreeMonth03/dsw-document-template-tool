#!/usr/bin/env python3
"""Align a Weblate review branch to a validated translation branch."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AlignResult:
    """Result of a Weblate review-branch alignment."""

    action: str
    target_revision: str
    previous_review_revision: str | None


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Reset a weblate/v* review branch to the checked-out translation/v* "
            "HEAD after the target branch has passed refresh checks."
        ),
    )
    parser.add_argument("--repo", required=True, help="Checked-out translation repository.")
    parser.add_argument(
        "--target-branch",
        required=True,
        help="Current translation/v* branch. Used for operator-facing validation.",
    )
    parser.add_argument(
        "--weblate-branch",
        required=True,
        help="Weblate review branch to create or reset.",
    )
    return parser


def main() -> None:
    """Run Weblate review-branch alignment."""

    args = build_argument_parser().parse_args()
    result = align_weblate_review_branch(
        repo=Path(args.repo).resolve(),
        target_branch=args.target_branch,
        weblate_branch=args.weblate_branch,
    )
    print(
        "INFO: Weblate review branch alignment "
        f"{result.action}: {args.weblate_branch} -> {result.target_revision}"
    )


def align_weblate_review_branch(
    *,
    repo: Path,
    target_branch: str,
    weblate_branch: str,
) -> AlignResult:
    """Align ``weblate_branch`` to the checked-out target HEAD when safe."""

    ensure_clean_worktree(repo)
    ensure_expected_target_branch(repo, target_branch)

    target_revision = capture(["git", "rev-parse", "HEAD"], cwd=repo).strip()
    review_revision = remote_branch_revision(repo, weblate_branch)

    if review_revision is None:
        run(["git", "push", "origin", f"HEAD:refs/heads/{weblate_branch}"], cwd=repo)
        return AlignResult(
            action="created",
            target_revision=target_revision,
            previous_review_revision=None,
        )

    fetch_remote_branch(repo, weblate_branch)
    if review_revision == target_revision:
        return AlignResult(
            action="unchanged",
            target_revision=target_revision,
            previous_review_revision=review_revision,
        )

    if not is_ancestor(repo, review_revision, "HEAD"):
        raise SystemExit(
            "Refusing to reset Weblate review branch because it contains "
            "unpromoted changes:\n"
            f"  branch: {weblate_branch}\n"
            f"  review revision: {review_revision}\n"
            f"  target revision: {target_revision}\n"
            "Run the Weblate promotion workflow first, then rerun translation sync."
        )

    run(
        [
            "git",
            "push",
            "origin",
            f"HEAD:refs/heads/{weblate_branch}",
            f"--force-with-lease=refs/heads/{weblate_branch}:{review_revision}",
        ],
        cwd=repo,
    )
    return AlignResult(
        action="updated",
        target_revision=target_revision,
        previous_review_revision=review_revision,
    )


def ensure_clean_worktree(repo: Path) -> None:
    """Fail before aligning a branch from a dirty checkout."""

    status = capture(["git", "status", "--short"], cwd=repo)
    if status.strip():
        raise SystemExit("Refusing to align Weblate branch from a dirty checkout:\n" + status)


def ensure_expected_target_branch(repo: Path, target_branch: str) -> None:
    """Ensure the current checkout is the branch the workflow claims to sync."""

    current_branch = capture(["git", "branch", "--show-current"], cwd=repo).strip()
    if current_branch and current_branch != target_branch:
        raise SystemExit(
            f"Refusing to align Weblate branch from {current_branch}; expected {target_branch}."
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


def fetch_remote_branch(repo: Path, branch: str) -> None:
    """Fetch a remote branch into refs/remotes/origin."""

    run(["git", "fetch", "origin", f"{branch}:refs/remotes/origin/{branch}"], cwd=repo)


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


def run(command: list[object], *, cwd: Path) -> None:
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
