#!/usr/bin/env python3
"""CLI entrypoint for translator-facing DSW template trees."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from dsw_document_template_tool.translation_tree import (
    audit_translated_template_structure,
    audit_translation_tree,
    export_translation_tree,
    export_xliff,
    import_xliff,
    merge_translation_tree,
    sync_translation_tree,
)

EXPANDED_WORKSPACE_HELP = "Expanded workspace directory."
SOURCE_LANG_HELP = "Source language code used by translation documents."
TARGET_LANG_HELP = "Target language code used by translation documents."
TRANSLATION_TREE_HELP = "Translation tree directory."

CommandHandler = Callable[[argparse.Namespace], None]


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
    export_parser.add_argument("--source", required=True, help=EXPANDED_WORKSPACE_HELP)
    export_parser.add_argument("--output", required=True, help=TRANSLATION_TREE_HELP)

    export_xliff_parser = subparsers.add_parser(
        "export-xliff",
        help="Export one translation tree to XLIFF.",
    )
    export_xliff_parser.add_argument("--tree", required=True, help=TRANSLATION_TREE_HELP)
    export_xliff_parser.add_argument("--output", required=True, help="XLIFF output path.")
    export_xliff_parser.add_argument(
        "--source-lang",
        default="en",
        help=SOURCE_LANG_HELP,
    )
    export_xliff_parser.add_argument(
        "--target-lang",
        default="zh_Hant",
        help=TARGET_LANG_HELP,
    )

    import_xliff_parser = subparsers.add_parser(
        "import-xliff",
        help="Import edited XLIFF targets back into a translation tree.",
    )
    import_xliff_parser.add_argument("--tree", required=True, help=TRANSLATION_TREE_HELP)
    import_xliff_parser.add_argument("--xliff", required=True, help="XLIFF file to import.")
    import_xliff_parser.add_argument(
        "--source-lang",
        default="en",
        help=SOURCE_LANG_HELP,
    )
    import_xliff_parser.add_argument(
        "--target-lang",
        default="zh_Hant",
        help=TARGET_LANG_HELP,
    )

    sync_parser = subparsers.add_parser(
        "sync",
        help="Apply one translation tree back into a generated expanded workspace.",
    )
    sync_parser.add_argument("--tree", required=True, help=TRANSLATION_TREE_HELP)
    sync_parser.add_argument("--source", required=True, help=EXPANDED_WORKSPACE_HELP)
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
        "--template-description",
        help="Optional description to write into the translated template.json.",
    )
    sync_parser.add_argument(
        "--template-version",
        help="Optional version to write into the translated template.json.",
    )
    sync_parser.add_argument(
        "--public-readme",
        help=(
            "Optional user-facing README.md to copy into the translated template output. "
            "Falls back to a generated README when the file is missing."
        ),
    )

    audit_parser = subparsers.add_parser(
        "audit",
        help="Check that translation blocks are safe for translators to edit.",
    )
    audit_parser.add_argument("--tree", required=True, help=TRANSLATION_TREE_HELP)
    audit_parser.add_argument("--source", required=True, help=EXPANDED_WORKSPACE_HELP)

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

    merge_parser = subparsers.add_parser(
        "merge",
        help="Merge existing translator edits into a regenerated translation tree.",
    )
    merge_parser.add_argument(
        "--old-tree",
        required=True,
        help="Existing translation tree containing reusable translator edits.",
    )
    merge_parser.add_argument(
        "--new-tree",
        required=True,
        help="Freshly exported translation tree skeleton.",
    )
    merge_parser.add_argument(
        "--output",
        required=True,
        help="Merged translation tree directory.",
    )
    merge_parser.add_argument(
        "--source-lang",
        default="en",
        help=SOURCE_LANG_HELP,
    )
    merge_parser.add_argument(
        "--target-lang",
        default="zh_Hant",
        help=TARGET_LANG_HELP,
    )
    merge_parser.add_argument(
        "--allow-sentence-matches",
        action="store_true",
        help=(
            "Also migrate unique visible sentence matches. Disabled by default because "
            "same text does not prove the same Jinja/HTML structure."
        ),
    )
    merge_parser.add_argument(
        "--existing-translation-policy",
        choices=("preserve", "replace"),
        default="preserve",
        help=(
            "Keep existing target translations, or replace them when an older-tree "
            "unit has the same source structure. Defaults to preserve."
        ),
    )
    return parser


def main() -> None:
    """Run the selected translation-tree command."""

    parser = build_argument_parser()
    args = parser.parse_args()
    handlers: dict[str, CommandHandler] = {
        "audit": _run_audit,
        "audit-output": _run_audit_output,
        "export": _run_export,
        "export-xliff": _run_export_xliff,
        "import-xliff": _run_import_xliff,
        "merge": _run_merge,
        "sync": _run_sync,
    }
    handlers[args.command](args)


def _run_export(args: argparse.Namespace) -> None:
    output_dir = export_translation_tree(source_dir=args.source, output_dir=args.output)
    print(f"SUCCESS: Translation tree written to {output_dir}")


def _run_export_xliff(args: argparse.Namespace) -> None:
    output_path = export_xliff(
        tree_dir=args.tree,
        output_path=args.output,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
    )
    print(f"SUCCESS: XLIFF written to {output_path}")


def _run_import_xliff(args: argparse.Namespace) -> None:
    report = import_xliff(
        tree_dir=args.tree,
        xliff_path=args.xliff,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
    )
    print(f"SUCCESS: Imported {report.imported_units} XLIFF unit(s)")


def _run_audit(args: argparse.Namespace) -> None:
    issues = audit_translation_tree(tree_dir=args.tree, source_dir=args.source)
    if issues:
        print(f"FAILURE: Found {len(issues)} unsafe translation block issue(s)")
        for issue in issues:
            print(f"- {issue.code}: {issue.location}")
            print(f"  {issue.message}")
        raise SystemExit(1)
    print("SUCCESS: Translation tree is safe for translator edits")


def _run_audit_output(args: argparse.Namespace) -> None:
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


def _run_merge(args: argparse.Namespace) -> None:
    report = merge_translation_tree(
        old_tree_dir=args.old_tree,
        new_tree_dir=args.new_tree,
        output_dir=args.output,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        allow_sentence_matches=args.allow_sentence_matches,
        existing_translation_policy=args.existing_translation_policy,
    )
    print(
        "SUCCESS: Merged translation tree "
        f"({report.migrated_units} migrated, "
        f"{report.updated_units} updated, "
        f"{report.preserved_units} preserved, "
        f"{report.untranslated_units} untranslated)"
    )


def _run_sync(args: argparse.Namespace) -> None:
    output_dir = sync_translation_tree(
        tree_dir=args.tree,
        source_dir=args.source,
        output_dir=args.output,
        template_organization_id=args.template_organization_id,
        template_id=args.template_id,
        template_name=args.template_name,
        template_description=args.template_description,
        template_version=args.template_version,
        public_readme_path=args.public_readme,
    )
    print(f"SUCCESS: Translated expanded template written to {output_dir}")


if __name__ == "__main__":
    main()
