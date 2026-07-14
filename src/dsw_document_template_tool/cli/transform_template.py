#!/usr/bin/env python3
"""CLI entrypoint for compact <-> expanded DSW template transforms."""

from __future__ import annotations

import argparse

from dsw_document_template_tool.template_transform import (
    compact_template_dir,
    expand_template_dir,
    explain_transform_workspace,
)

COMPACT_TEMPLATE_HELP = "Compact template directory."
EXPANDED_WORKSPACE_HELP = "Expanded workspace directory."


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Expand or compact DSW document templates for translation workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    expand_parser = subparsers.add_parser(
        "expand",
        help="Expand one compact template into a translation-friendly workspace.",
    )
    expand_parser.add_argument("--source", required=True, help=COMPACT_TEMPLATE_HELP)
    expand_parser.add_argument("--output", required=True, help=EXPANDED_WORKSPACE_HELP)
    expand_parser.add_argument(
        "--no-local-patches",
        action="store_true",
        help=(
            "Skip local zh-Hant patches such as package metadata, CJK fonts, and localized "
            "source-level helper rewrites. "
            "Use this for compact-vs-expanded render regression only."
        ),
    )

    compact_parser = subparsers.add_parser(
        "compact",
        help="Compact one expanded workspace back into DSW uploadable form.",
    )
    compact_parser.add_argument("--source", required=True, help=EXPANDED_WORKSPACE_HELP)
    compact_parser.add_argument("--output", required=True, help=COMPACT_TEMPLATE_HELP)

    explain_parser = subparsers.add_parser(
        "explain",
        help="Show the profile and exact rewrite groups applied during expansion.",
    )
    explain_parser.add_argument("--source", required=True, help=EXPANDED_WORKSPACE_HELP)
    return parser


def main() -> None:
    """Run the selected transform command."""

    parser = build_argument_parser()
    args = parser.parse_args()

    if args.command == "expand":
        output_dir = expand_template_dir(
            source_dir=args.source,
            output_dir=args.output,
            apply_local_patches=not args.no_local_patches,
        )
        print(f"SUCCESS: Expanded template written to {output_dir}")
        return

    if args.command == "compact":
        output_dir = compact_template_dir(source_dir=args.source, output_dir=args.output)
        print(f"SUCCESS: Compacted template written to {output_dir}")
        return

    print(explain_transform_workspace(args.source))


if __name__ == "__main__":
    main()
