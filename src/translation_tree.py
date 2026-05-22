#!/usr/bin/env python3
"""CLI entrypoint for translator-facing DSW template trees."""

from __future__ import annotations

import argparse

from dsw_document_template_tool.translation_tree import (
    export_translation_tree,
    sync_translation_tree,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Export or sync translator-facing trees for DSW document templates.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export",
        help="Export one expanded workspace into unit-by-unit translation files.",
    )
    export_parser.add_argument("--source", required=True, help="Expanded workspace directory.")
    export_parser.add_argument("--output", required=True, help="Translation tree directory.")

    sync_parser = subparsers.add_parser(
        "sync",
        help="Apply one translation tree back into a generated expanded workspace.",
    )
    sync_parser.add_argument("--tree", required=True, help="Translation tree directory.")
    sync_parser.add_argument("--source", required=True, help="Expanded workspace directory.")
    sync_parser.add_argument("--output", required=True, help="Translated expanded directory.")
    return parser


def main() -> None:
    """Run the selected translation-tree command."""

    parser = build_argument_parser()
    args = parser.parse_args()

    if args.command == "export":
        output_dir = export_translation_tree(source_dir=args.source, output_dir=args.output)
        print(f"SUCCESS: Translation tree written to {output_dir}")
        return

    output_dir = sync_translation_tree(
        tree_dir=args.tree,
        source_dir=args.source,
        output_dir=args.output,
    )
    print(f"SUCCESS: Translated expanded template written to {output_dir}")


if __name__ == "__main__":
    main()
