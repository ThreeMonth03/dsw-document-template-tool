#!/usr/bin/env python3
"""Report whether translation version branches have pending migrations."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dsw_document_template_tool.translation_migration import (  # noqa: E402
    TranslationRepositoryConfig,
    load_translation_repository_config,
    target_versions,
    version_policy_decision,
)


@dataclass(frozen=True)
class SourceMigrationStatus:
    """Migration dry-run status for one source version."""

    source_version: str
    target_versions: list[str]
    pending: bool
    error: bool
    summary_lines: list[str]


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Run exact-only migration dry-runs for active translation version "
            "branches and summarize whether any migration PRs are pending."
        ),
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Translation repository checkout containing translation-config.yml.",
    )
    parser.add_argument(
        "--tooling-root",
        required=True,
        help="Checked-out tooling repository.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml relative to --repo.",
    )
    parser.add_argument(
        "--source-version",
        action="append",
        default=[],
        help=(
            "Source version tag to check. May be repeated. Defaults to versions "
            "whose effective version_policy.refresh is auto."
        ),
    )
    parser.add_argument(
        "--target-version",
        action="append",
        default=[],
        help=(
            "Target version tag to check. May be repeated and is applied to each "
            "source. Defaults to versions whose version_policy.migrate_into is auto."
        ),
    )
    parser.add_argument(
        "--clean-artifact-root",
        default=os.environ.get("TRANSLATION_CLEAN_ARTIFACT_ROOT", ""),
        help=(
            "Downloaded clean upstream scaffold artifact root. Defaults to "
            "TRANSLATION_CLEAN_ARTIFACT_ROOT when set."
        ),
    )
    parser.add_argument(
        "--tdk-executable",
        help="Path to dsw-tdk. Defaults to <tooling-root>/.venv/bin/dsw-tdk.",
    )
    parser.add_argument(
        "--json-report",
        help="Optional path for a machine-readable status report.",
    )
    parser.add_argument(
        "--fail-on-pending",
        action="store_true",
        help="Exit with status 1 when dry-run migrations would create changes.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full migration dry-run output for each source version.",
    )
    return parser


def main() -> None:
    """Run migration status checks."""

    args = build_argument_parser().parse_args()
    repo = Path(args.repo).resolve()
    tooling_root = Path(args.tooling_root).resolve()
    config = load_translation_repository_config(repo / args.config)
    source_versions = args.source_version or default_source_versions(config)
    clean_artifact_root = (
        Path(args.clean_artifact_root).resolve() if args.clean_artifact_root else None
    )
    if clean_artifact_root is not None and not clean_artifact_root.is_dir():
        raise SystemExit(
            f"--clean-artifact-root does not exist or is not a directory: {clean_artifact_root}"
        )

    statuses = [
        check_source_version(
            repo=repo,
            tooling_root=tooling_root,
            source_version=source_version,
            target_version_args=args.target_version,
            clean_artifact_root=clean_artifact_root,
            tdk_executable=args.tdk_executable,
            verbose=args.verbose,
        )
        for source_version in source_versions
    ]
    write_report(statuses, Path(args.json_report) if args.json_report else None)
    print_human_summary(statuses)

    if any(status.error for status in statuses):
        raise SystemExit(2)
    if args.fail_on_pending and any(status.pending for status in statuses):
        raise SystemExit(1)


def default_source_versions(config: TranslationRepositoryConfig) -> list[str]:
    """Return versions whose checked-in translation branches are expected to be fresh."""

    return [
        version
        for version in config.template.supported_versions
        if version_policy_decision(config, version).refresh == "auto"
    ]


def check_source_version(
    *,
    repo: Path,
    tooling_root: Path,
    source_version: str,
    target_version_args: list[str],
    clean_artifact_root: Path | None,
    tdk_executable: str | None,
    verbose: bool,
) -> SourceMigrationStatus:
    """Run the existing migration helper in dry-run mode for one source version."""

    config = load_translation_repository_config(repo / "translation-config.yml")
    targets = target_versions(
        config,
        source_version,
        requested_targets=target_version_args or None,
    )
    command = [
        sys.executable,
        str(tooling_root / "scripts" / "ci" / "create_translation_migration_prs.py"),
        "--repo",
        str(repo),
        "--tooling-root",
        str(tooling_root),
        "--source-version",
        source_version,
        "--dry-run",
    ]
    for target_version in target_version_args:
        command.extend(["--target-version", target_version])
    if clean_artifact_root is not None:
        command.extend(["--clean-artifact-root", str(clean_artifact_root)])
    if tdk_executable:
        command.extend(["--tdk-executable", tdk_executable])

    result = subprocess.run(
        command,
        cwd=tooling_root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if verbose or result.returncode != 0:
        print(f"===== migration dry-run: {source_version} =====")
        print(output.rstrip())

    summary_lines = summarize_output(output)
    return SourceMigrationStatus(
        source_version=source_version,
        target_versions=targets,
        pending=is_pending_output(output),
        error=result.returncode != 0,
        summary_lines=summary_lines,
    )


def summarize_output(output: str) -> list[str]:
    """Extract stable, human-useful migration dry-run lines."""

    prefixes = (
        "INFO: [",
        "INFO: No target versions",
        "ERROR:",
        "Traceback",
    )
    return [
        line
        for line in output.splitlines()
        if line.startswith(prefixes) or "dry run; not committing" in line
    ]


def is_pending_output(output: str) -> bool:
    """Return whether dry-run output indicates a migration PR would be needed."""

    return "changed paths:" in output or "dry run; not committing" in output


def write_report(statuses: list[SourceMigrationStatus], report_path: Path | None) -> None:
    """Write an optional JSON report for CI artifacts."""

    if report_path is None:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps([asdict(status) for status in statuses], indent=2) + "\n",
        encoding="utf-8",
    )


def print_human_summary(statuses: list[SourceMigrationStatus]) -> None:
    """Print a short status summary suitable for operator logs."""

    print("Translation migration status:")
    if not statuses:
        print("- No source versions are enabled for migration checks.")
        return
    for status in statuses:
        state = migration_state_label(status)
        targets = ", ".join(status.target_versions) or "(no targets)"
        print(f"- {status.source_version}: {state}; targets: {targets}")
        for line in status.summary_lines:
            print(f"  {line}")


def migration_state_label(status: SourceMigrationStatus) -> str:
    """Return the operator-facing state label for one migration source."""

    if status.error:
        return "ERROR"
    if status.pending:
        return "PENDING"
    return "OK"


if __name__ == "__main__":
    main()
