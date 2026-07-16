#!/usr/bin/env python3
"""CLI entrypoint for the headless DSW document template regression workflow."""

from __future__ import annotations

import argparse
import sys

from dsw_document_template_tool import (
    DEFAULT_WORKFLOW_CONFIG_PATH,
    DocumentTemplateWorkflowService,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Run headless DSW template regression against fixture projects.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_WORKFLOW_CONFIG_PATH),
        help="Workflow YAML config path.",
    )
    return parser


def main() -> None:
    """Run the configured regression workflow and exit non-zero on failure."""

    args = build_argument_parser().parse_args()
    service = DocumentTemplateWorkflowService()
    report = service.run(args.config)
    print(f"INFO: Wrote regression report to {report.report_path}")
    if report.passed:
        if report.assertion == "render_success":
            print("SUCCESS: All fixtures rendered successfully")
        else:
            print("SUCCESS: All fixtures matched")
        return
    if report.assertion == "render_success":
        print("FAILURE: One or more fixtures failed to render")
    else:
        print("FAILURE: One or more fixtures diverged")
    sys.exit(1)


if __name__ == "__main__":
    main()
