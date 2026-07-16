#!/usr/bin/env python3
"""Verify and summarize one DSW runtime's complete regression evidence."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dsw_document_template_tool.runtime_evidence import (
    collect_runtime_evidence,
    write_runtime_evidence,
)


def main() -> None:
    """Write evidence reports and fail when any required proof is missing."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compat-config", type=Path, required=True)
    parser.add_argument("--evidence-config", type=Path, required=True)
    parser.add_argument("--metamodel-version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--preview-root", type=Path, required=True)
    parser.add_argument("--regression-root", type=Path, required=True)
    parser.add_argument("--source-template-id", required=True)
    parser.add_argument("--translation-locale", required=True)
    args = parser.parse_args()

    report = collect_runtime_evidence(
        compat_config=args.compat_config,
        evidence_config=args.evidence_config,
        metamodel_version=args.metamodel_version,
        plan_path=args.plan,
        preview_root=args.preview_root,
        regression_root=args.regression_root,
        source_template_id=args.source_template_id,
        translation_locale=args.translation_locale,
    )
    json_path, markdown_path = write_runtime_evidence(report, args.output_dir)
    print(f"INFO: Wrote runtime evidence to {json_path} and {markdown_path}")
    _append_step_summary(markdown_path)
    if not report.passed:
        raise SystemExit("Runtime evidence is incomplete; see evidence.md")


def _append_step_summary(markdown_path: Path) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as summary:
        summary.write("\n\n")
        summary.write(markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
