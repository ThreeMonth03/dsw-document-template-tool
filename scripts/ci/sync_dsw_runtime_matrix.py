#!/usr/bin/env python3
"""Keep the GitHub Actions DSW runtime matrix aligned with config."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dsw_document_template_tool.translation_migration import preview_runtime_matrix  # noqa: E402

DEFAULT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "headless_render_regression.yml"
START_MARKER = "          # BEGIN GENERATED DSW RUNTIME MATRIX"
END_MARKER = "          # END GENERATED DSW RUNTIME MATRIX"
MATRIX_ITEM_INDENT = "          "
MATRIX_FIELD_INDENT = "            "


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="sync the checked-in GitHub Actions DSW runtime matrix",
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        default=DEFAULT_WORKFLOW,
        help="Workflow file containing the generated DSW runtime matrix block.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the workflow matrix is not already synchronized.",
    )
    args = parser.parse_args()

    workflow_path = args.workflow
    original = workflow_path.read_text(encoding="utf-8")
    updated = sync_runtime_matrix(original)

    if args.check:
        if updated != original:
            print("ERROR: DSW runtime matrix is out of sync.", file=sys.stderr)
            print(
                "".join(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        updated.splitlines(keepends=True),
                        fromfile=str(workflow_path),
                        tofile=f"{workflow_path} (expected)",
                    )
                ),
                file=sys.stderr,
            )
            raise SystemExit(1)
        return

    if updated != original:
        workflow_path.write_text(updated, encoding="utf-8")


def sync_runtime_matrix(workflow_text: str) -> str:
    """Return workflow text with the generated matrix block refreshed."""

    generated_body = render_runtime_matrix_block()
    pattern = re.compile(
        rf"(?P<start>{re.escape(START_MARKER)}\n)"
        rf"(?P<body>.*?)"
        rf"(?P<end>{re.escape(END_MARKER)})",
        re.DOTALL,
    )
    match = pattern.search(workflow_text)
    if match is None:
        raise SystemExit("ERROR: Could not find generated DSW runtime matrix markers in workflow")
    return (
        workflow_text[: match.start("body")] + generated_body + workflow_text[match.start("end") :]
    )


def render_runtime_matrix_block() -> str:
    """Render the runtime matrix rows using stable YAML formatting."""

    lines: list[str] = []
    for row in preview_runtime_matrix():
        for index, (key, value) in enumerate(row.items()):
            prefix = f"{MATRIX_ITEM_INDENT}- " if index == 0 else MATRIX_FIELD_INDENT
            lines.append(f"{prefix}{key}: {json.dumps(value)}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
