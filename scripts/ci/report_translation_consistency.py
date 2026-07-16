#!/usr/bin/env python3
"""Generate a non-blocking cross-version translation consistency report."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dsw_document_template_tool.translation_repository import (  # noqa: E402
    fetch_version_branches,
    inspect_translation_repository,
    load_translation_repository_config,
    render_consistency_markdown,
    report_as_json,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build command-line arguments for local and Actions use."""

    parser = argparse.ArgumentParser(
        description=(
            "Compare visible source sentences and translated targets across active "
            "version branches without changing repository content."
        )
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Translation repository checkout containing translation-config.yml.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Configuration path relative to --repo.",
    )
    parser.add_argument(
        "--version",
        action="append",
        default=[],
        help=(
            "Version tag to inspect. May be repeated. Defaults to all active and "
            "maintenance versions."
        ),
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch remote version branches using the configured branch prefix before reading.",
    )
    parser.add_argument(
        "--json-report",
        required=True,
        help="Output path for the complete machine-readable report.",
    )
    parser.add_argument(
        "--markdown-report",
        required=True,
        help="Output path for the complete human-readable report.",
    )
    parser.add_argument(
        "--summary",
        default=os.environ.get("GITHUB_STEP_SUMMARY", ""),
        help="Optional Actions job summary path. Defaults to GITHUB_STEP_SUMMARY.",
    )
    parser.add_argument(
        "--summary-limit",
        type=int,
        default=20,
        help="Maximum findings rendered into the Actions summary.",
    )
    return parser


def main() -> None:
    """Generate JSON, Markdown, and optional Actions summary outputs."""

    args = build_argument_parser().parse_args()
    if args.summary_limit < 0:
        raise SystemExit("--summary-limit must be zero or greater")

    repo = Path(args.repo).resolve()
    config = load_translation_repository_config(repo / args.config)
    if args.fetch:
        fetch_version_branches(repo=repo, config=config)
    report = inspect_translation_repository(
        repo=repo,
        config=config,
        versions=args.version or None,
    )
    json_path = Path(args.json_report)
    markdown_path = Path(args.markdown_report)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(report_as_json(report), encoding="utf-8")
    markdown_path.write_text(render_consistency_markdown(report), encoding="utf-8")

    if args.summary:
        summary_path = Path(args.summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(render_consistency_markdown(report, max_findings=args.summary_limit))
            handle.write("\n")

    print(
        "Cross-version translation consistency: "
        f"{len(report.findings)} finding(s), "
        f"{report.translation_gap_count} gap(s), "
        f"{report.wording_drift_count} wording drift(s)."
    )


if __name__ == "__main__":
    main()
