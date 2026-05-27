#!/usr/bin/env python3
"""CLI entrypoint for translator-facing DSW template trees."""

from __future__ import annotations

import argparse

from dsw_document_template_tool.translation_tree import (
    audit_translated_template_structure,
    audit_translation_tree,
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
    sync_parser.add_argument(
        "--template-organization-id",
        help="Optional organizationId to write into the translated template.json.",
    )
    sync_parser.add_argument(
        "--template-id",
        help="Optional templateId to write into the translated template.json.",
    )
    sync_parser.add_argument(
        "--template-name",
        help="Optional name to write into the translated template.json.",
    )
    sync_parser.add_argument(
        "--template-version",
        help="Optional version to write into the translated template.json.",
    )

    audit_parser = subparsers.add_parser(
        "audit",
        help="Check that translation blocks are safe for translators to edit.",
    )
    audit_parser.add_argument("--tree", required=True, help="Translation tree directory.")
    audit_parser.add_argument("--source", required=True, help="Expanded workspace directory.")

    audit_output_parser = subparsers.add_parser(
        "audit-output",
        help="Check that translated output kept the expanded template structure.",
    )
    audit_output_parser.add_argument(
        "--source",
        required=True,
        help="Expanded workspace directory used as the structural baseline.",
    )
    audit_output_parser.add_argument(
        "--output",
        required=True,
        help="Translated expanded template output directory.",
    )
    return parser


def main() -> None:
    """Run the selected translation-tree command."""

    parser = build_argument_parser()
    args = parser.parse_args()

    if args.command == "export":
        output_dir = export_translation_tree(source_dir=args.source, output_dir=args.output)
        print(f"SUCCESS: Translation tree written to {output_dir}")
        return

    if args.command == "audit":
        issues = audit_translation_tree(tree_dir=args.tree, source_dir=args.source)
        if issues:
            print(f"FAILURE: Found {len(issues)} unsafe translation block issue(s)")
            for issue in issues:
                print(f"- {issue.code}: {issue.location}")
                print(f"  {issue.message}")
            raise SystemExit(1)
        print("SUCCESS: Translation tree is safe for translator edits")
        return

    if args.command == "audit-output":
        issues = audit_translated_template_structure(
            source_dir=args.source,
            output_dir=args.output,
        )
        if issues:
            print(f"FAILURE: Found {len(issues)} translated output structure issue(s)")
            for issue in issues:
                print(f"- {issue.code}: {issue.location}")
                print(f"  {issue.message}")
            raise SystemExit(1)
        print("SUCCESS: Translated output keeps the expanded template structure")
        return

    output_dir = sync_translation_tree(
        tree_dir=args.tree,
        source_dir=args.source,
        output_dir=args.output,
        template_organization_id=args.template_organization_id,
        template_id=args.template_id,
        template_name=args.template_name,
        template_version=args.template_version,
    )
    print(f"SUCCESS: Translated expanded template written to {output_dir}")


if __name__ == "__main__":
    main()
