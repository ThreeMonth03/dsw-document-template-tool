#!/usr/bin/env python3
"""Validate a translation workflow configuration."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from resolve_upstream_refs import normalize_git_remote  # noqa: E402

from dsw_document_template_tool.translation_migration import (  # noqa: E402
    TranslationMigrationError,
    TranslationRepositoryConfig,
    load_translation_repository_config,
    version_policy_decision,
)


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="validate a DSW document-template translation configuration",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("translation-config.yml"),
        help="Path to translation-config.yml.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        help="Optional GitHub step summary file to append a Markdown report to.",
    )
    args = parser.parse_args()

    try:
        config = load_translation_repository_config(args.config)
        missing_tags = missing_upstream_tags(config)
        if missing_tags:
            raise TranslationMigrationError(
                "Missing upstream tags: " + ", ".join(missing_tags),
            )

        report = render_summary(config)
        print(report)
        if args.summary is not None:
            append_summary(args.summary, report)
    except (OSError, subprocess.CalledProcessError, TranslationMigrationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def missing_upstream_tags(config: TranslationRepositoryConfig) -> list[str]:
    """Return configured supported versions that do not exist upstream."""

    missing: list[str] = []
    for version in config.template.supported_versions:
        if not remote_tag_exists(config.template.upstream_repository, version):
            missing.append(version)
    return missing


def remote_tag_exists(remote: str, tag: str) -> bool:
    """Return whether a remote contains a concrete tag ref."""

    result = subprocess.run(
        [
            "git",
            "ls-remote",
            "--exit-code",
            "--tags",
            normalize_git_remote(remote),
            f"refs/tags/{tag}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def render_summary(config: TranslationRepositoryConfig) -> str:
    """Render a concise validation report."""

    versions = ", ".join(config.template.supported_versions)
    policy_rows = [
        "| Version | State | Refresh | Migrate Into | Release Assets |",
        "| --- | --- | --- | --- | --- |",
    ]
    for version in config.template.supported_versions:
        policy = version_policy_decision(config, version)
        policy_rows.append(
            "| "
            + " | ".join(
                (
                    f"`{version}`",
                    f"`{policy.state}`",
                    f"`{policy.refresh}`",
                    f"`{policy.migrate_into}`",
                    f"`{str(policy.publish_release).lower()}`",
                )
            )
            + " |"
        )
    lines = [
        "## Translation workflow",
        "",
        f"- Upstream repository: `{config.template.upstream_repository}`",
        f"- Supported versions: `{versions}`",
        f"- Control branch: `{config.branches.control_branch}`",
        f"- Version branch prefix: `{config.branches.version_branch_prefix}`",
        "- Translated template description: "
        f"`{config.translation.translated_template_description or ''}`",
        f"- Public README path: `{config.public_readme.path.as_posix()}`",
        f"- Cross-version sync mode: `{config.migration.mode}`",
        f"- XLIFF exchange: `{'enabled' if config.xliff_exchange.enabled else 'disabled'}`",
        "",
        "## Version lifecycle",
        "",
        *policy_rows,
        "",
        "All configured upstream tags exist.",
        "Branch refresh creates or updates only versions whose policy allows refresh.",
        "Automatic cross-version sync uses only versions with `migrate_into: auto`.",
        "Versions with `refresh: false` remain scaffold-only records until maintainers opt in.",
        "",
    ]
    return "\n".join(lines)


def append_summary(path: Path, report: str) -> None:
    """Append a report to a GitHub step summary path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as summary_file:
        summary_file.write(report)


if __name__ == "__main__":
    main()
