#!/usr/bin/env python3
"""Resolve the source template version for translation migration jobs."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="resolve the source version used by translation migration automation",
    )
    parser.add_argument("--event-name", required=True, help="GitHub event name.")
    parser.add_argument(
        "--manual-source-version",
        default="",
        help="Workflow-dispatch source_version input.",
    )
    parser.add_argument(
        "--workflow-run-head-branch",
        default="",
        help="Head branch from a workflow_run event.",
    )
    parser.add_argument(
        "--previous-latest-version",
        default="",
        help="Latest supported version before syncing clean artifacts.",
    )
    parser.add_argument(
        "--current-latest-version",
        default="",
        help="Latest supported version after syncing clean artifacts.",
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        help="Optional GitHub Actions output file.",
    )
    args = parser.parse_args()

    result = resolve_migration_source(
        event_name=args.event_name,
        manual_source_version=args.manual_source_version,
        workflow_run_head_branch=args.workflow_run_head_branch,
        previous_latest_version=args.previous_latest_version,
        current_latest_version=args.current_latest_version,
    )
    if args.github_output is not None:
        write_github_output(args.github_output, result)

    if result.skip:
        print("No translation version source branch found; skipping.")
    else:
        print(f"Using migration source version: {result.source_version}")


class MigrationSourceResult:
    """Resolved migration source decision."""

    def __init__(self, *, skip: bool, source_version: str = "") -> None:
        self.skip = skip
        self.source_version = source_version


def resolve_migration_source(
    *,
    event_name: str,
    manual_source_version: str,
    workflow_run_head_branch: str,
    previous_latest_version: str,
    current_latest_version: str,
) -> MigrationSourceResult:
    """Resolve the migration source version from event context."""

    source_version = manual_source_version.strip()

    if not source_version and event_name == "workflow_run":
        prefix = "translation/"
        if not workflow_run_head_branch.startswith(prefix):
            return MigrationSourceResult(skip=True)
        source_version = workflow_run_head_branch.removeprefix(prefix)

    if not source_version:
        source_version = previous_latest_version.strip() or current_latest_version.strip()

    return MigrationSourceResult(skip=False, source_version=source_version)


def write_github_output(path: Path, result: MigrationSourceResult) -> None:
    """Write the decision to a GitHub Actions output file."""

    lines = [f"skip={str(result.skip).lower()}"]
    if result.source_version:
        lines.append(f"source_version={result.source_version}")
    with path.open("a", encoding="utf-8") as output_file:
        output_file.write("\n".join(lines))
        output_file.write("\n")


if __name__ == "__main__":
    main()
