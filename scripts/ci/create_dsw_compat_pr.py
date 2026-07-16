#!/usr/bin/env python3
"""Open a compatibility probe PR for unsupported upstream DSW metamodels."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dsw_document_template_tool.compat_probe import (
    build_probe_plan,
    default_branch_for_plan,
    default_title_for_plan,
    render_compat_config,
    render_evidence_config,
    render_pr_body,
    render_probe_report,
)

DEFAULT_COMPAT_PATH = Path("config/dsw-compat.yml")
DEFAULT_EVIDENCE_PATH = Path("config/regression-evidence.yml")
DEFAULT_REPORT_PATH = Path("docs/compatibility/dsw-compatibility-probe.md")


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="create or update a DSW compatibility probe pull request",
    )
    parser.add_argument("--report", type=Path, required=True, help="Discovery report file.")
    parser.add_argument(
        "--compat",
        type=Path,
        default=DEFAULT_COMPAT_PATH,
        help="DSW compatibility config file to update with probe runtimes.",
    )
    parser.add_argument(
        "--evidence-config",
        type=Path,
        default=DEFAULT_EVIDENCE_PATH,
        help="Regression evidence config whose runtime assignment block is updated.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to commit the report to.",
    )
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub repository, for example owner/name.",
    )
    parser.add_argument(
        "--base",
        default=os.environ.get("GITHUB_REF_NAME", "master"),
        help="Base branch for the probe PR.",
    )
    parser.add_argument(
        "--branch",
        default="",
        help="Branch to push the probe changes to. Defaults to a metamodel-specific name.",
    )
    parser.add_argument("--title", default="", help="Pull request title.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the report locally but do not commit, push, or create a PR.",
    )
    args = parser.parse_args()

    if not args.repository:
        raise SystemExit("--repository is required when GITHUB_REPOSITORY is not set")
    if not args.report.is_file():
        raise SystemExit(f"Report file does not exist: {args.report}")
    if not args.compat.is_file():
        raise SystemExit(f"Compatibility config does not exist: {args.compat}")
    if not args.evidence_config.is_file():
        raise SystemExit(f"Regression evidence config does not exist: {args.evidence_config}")

    report = args.report.read_text(encoding="utf-8").strip()
    evidence_text = args.evidence_config.read_text(encoding="utf-8")
    initial_plan = build_probe_plan(
        report=report,
        compat_text=args.compat.read_text(encoding="utf-8"),
        evidence_text=evidence_text,
    )
    branch = args.branch or default_branch_for_plan(initial_plan)
    title = args.title or default_title_for_plan(initial_plan)

    if args.dry_run:
        rendered_report = render_probe_report(report, plan=initial_plan)
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(rendered_report, encoding="utf-8")
        print(f"INFO: wrote {args.report_path} (dry run)")
        return

    branch_existed = checkout_start_ref(branch=branch, base=args.base)
    if not args.compat.is_file():
        raise SystemExit(f"Compatibility config does not exist on probe branch: {args.compat}")
    if args.evidence_config.is_file():
        evidence_text = args.evidence_config.read_text(encoding="utf-8")
    plan = build_probe_plan(
        report=report,
        compat_text=args.compat.read_text(encoding="utf-8"),
        evidence_text=evidence_text,
    )
    rendered_report = render_probe_report(report, plan=plan)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(rendered_report, encoding="utf-8")
    args.compat.write_text(render_compat_config(plan.runtimes), encoding="utf-8")
    args.evidence_config.write_text(
        render_evidence_config(evidence_text, plan.runtime_knowledge_models),
        encoding="utf-8",
    )

    run(["git", "add", str(args.report_path), str(args.compat), str(args.evidence_config)])

    if not has_staged_changes():
        if branch_existed:
            print("INFO: Compatibility probe is unchanged; ensuring PR exists.")
            create_or_update_pr(
                repository=args.repository,
                branch=branch,
                base=args.base,
                title=title,
                body=render_pr_body(args.report_path, plan=plan),
            )
            return
        print("INFO: Compatibility probe is unchanged; no remote branch to update.")
        return

    configure_git_identity()
    run(["git", "commit", "-m", "ci: probe DSW metamodel compatibility"])
    run(["git", "push", "--force-with-lease", "origin", f"HEAD:refs/heads/{branch}"])
    create_or_update_pr(
        repository=args.repository,
        branch=branch,
        base=args.base,
        title=title,
        body=render_pr_body(args.report_path, plan=plan),
    )


def configure_git_identity() -> None:
    """Configure a deterministic CI git identity when none is set."""

    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])


def checkout_start_ref(*, branch: str, base: str) -> bool:
    """Check out the automation start point without binding a local branch.

    The workflow pushes the generated commit with ``HEAD:refs/heads/<branch>``,
    so a local branch is unnecessary. Staying detached avoids failures when a
    maintainer already has the automation branch checked out in another
    worktree.
    """

    if remote_branch_exists(branch):
        run(["git", "fetch", "origin", f"refs/heads/{branch}:refs/remotes/origin/{branch}"])
        run(["git", "checkout", "--detach", f"origin/{branch}"])
        return True
    run(["git", "checkout", "--detach", fetch_base_ref(base)])
    return False


def fetch_base_ref(base: str) -> str:
    """Fetch and return the origin ref used to start a new automation branch."""

    origin_ref = f"origin/{base}"
    fetch_result = subprocess.run(
        ["git", "fetch", "origin", f"refs/heads/{base}:refs/remotes/{origin_ref}"],
        check=False,
    )
    if fetch_result.returncode != 0 or not git_ref_exists(origin_ref):
        raise SystemExit(
            f"Base branch origin/{base} does not exist or could not be fetched. "
            "Refusing to create a compatibility PR from the current checkout HEAD."
        )
    return origin_ref


def remote_branch_exists(branch: str) -> bool:
    """Return whether the remote automation branch already exists."""

    return (
        subprocess.run(
            ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def git_ref_exists(ref: str) -> bool:
    """Return whether a local git ref exists."""

    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def has_staged_changes() -> bool:
    """Return whether the index has staged changes."""

    return (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            check=False,
        ).returncode
        != 0
    )


def create_or_update_pr(
    *,
    repository: str,
    branch: str,
    base: str,
    title: str,
    body: str,
) -> None:
    """Create or update the probe pull request."""

    body_file = Path(".cache/dsw-compat-pr-body.md")
    body_file.parent.mkdir(parents=True, exist_ok=True)
    body_file.write_text(body + "\n", encoding="utf-8")

    existing = subprocess.run(
        ["gh", "pr", "view", branch, "--repo", repository, "--json", "url", "--jq", ".url"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        run(
            [
                "gh",
                "pr",
                "edit",
                branch,
                "--repo",
                repository,
                "--title",
                title,
                "--body-file",
                str(body_file),
            ]
        )
        print(f"INFO: Updated existing PR: {existing.stdout.strip()}")
        return

    run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repository,
            "--base",
            base,
            "--head",
            branch,
            "--title",
            title,
            "--body-file",
            str(body_file),
        ]
    )


def run(args: list[str]) -> None:
    """Run a command."""

    subprocess.run(args, check=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
