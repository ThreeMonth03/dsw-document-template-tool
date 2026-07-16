"""Write scaffold preview status metadata for CI artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--status", required=True, choices=("failed",))
    parser.add_argument("--reason", required=True)
    parser.add_argument("--template-version")
    parser.add_argument("--template-metamodel-version", required=True)
    parser.add_argument("--preview-metamodel-version", required=True)
    parser.add_argument("--exit-code", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    payload: dict[str, Any] = {
        "status": args.status,
        "reason": args.reason,
        "template_metamodel_version": args.template_metamodel_version,
        "preview_metamodel_version": args.preview_metamodel_version,
    }
    if args.template_version:
        payload["template_version"] = args.template_version
    if args.exit_code is not None:
        payload["exit_code"] = args.exit_code
    if dsw_version := os.environ.get("DSW_VERSION"):
        payload["dsw_version"] = dsw_version

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
