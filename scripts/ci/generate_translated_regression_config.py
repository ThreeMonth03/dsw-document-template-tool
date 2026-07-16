#!/usr/bin/env python3
"""Generate full render-regression config for one translated template package."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_document_template_tool.regression_config import (
    select_regression_knowledge_model_for_metamodel,
    write_package_render_config,
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]


def main() -> None:
    """Generate and write a translated-package render config."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument(
        "--compat-config",
        type=Path,
        default=REPO_ROOT / "config" / "dsw-compat.yml",
    )
    parser.add_argument(
        "--evidence-config",
        type=Path,
        default=REPO_ROOT / "config" / "regression-evidence.yml",
    )
    parser.add_argument("--metamodel-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()

    try:
        knowledge_model = select_regression_knowledge_model_for_metamodel(
            compat_config=args.compat_config,
            evidence_config=args.evidence_config,
            metamodel_version=args.metamodel_version,
        )
        write_package_render_config(
            base_config=args.base_config,
            output=args.output,
            output_dir=args.output_dir,
            package_path=args.package,
            knowledge_model_path=knowledge_model.path,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"INFO: Generated translated package regression config at {args.output}")


if __name__ == "__main__":
    main()
