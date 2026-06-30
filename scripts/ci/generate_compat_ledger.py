#!/usr/bin/env python3
"""Generate offline upstream compatibility ledgers for built workspaces."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dsw_document_template_tool.compat_ledger import write_compat_ledger  # noqa: E402


def main() -> None:
    """Run the compatibility ledger generator."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scaffold-root", type=Path)
    parser.add_argument("--source-lang", default="en")
    parser.add_argument("--source-template-id", required=True)
    parser.add_argument("--target-lang", default="zh_Hant")
    parser.add_argument("--workspace-root", type=Path, required=True)
    args = parser.parse_args()

    entries = write_compat_ledger(
        workspace_root=args.workspace_root,
        output_dir=args.output_dir,
        source_template_id=args.source_template_id,
        scaffold_root=args.scaffold_root,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
    )
    versions = ", ".join(str(entry["version"]) for entry in entries)
    print(f"SUCCESS: Compatibility ledger written for {versions} at {args.output_dir}")


if __name__ == "__main__":
    main()
