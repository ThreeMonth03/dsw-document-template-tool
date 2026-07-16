#!/usr/bin/env python3
"""Generate a version-aware regression config from built upstream workspaces."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_document_template_tool.regression_config import (
    select_regression_knowledge_model,
    select_regression_workspace,
    write_workspace_regression_config,
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]


def main() -> None:
    """Generate and write the requested regression config."""

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
    parser.add_argument("--metamodel-version", default="")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-dir-suffix", default="")
    parser.add_argument("--source-template-id", required=True)
    parser.add_argument("--version", default="latest")
    parser.add_argument("--workspace-root", type=Path, required=True)
    args = parser.parse_args()

    try:
        workspace = select_regression_workspace(
            workspace_root=args.workspace_root,
            source_template_id=args.source_template_id,
            version=args.version,
            metamodel_version=args.metamodel_version,
        )
        knowledge_model = select_regression_knowledge_model(
            compat_config=args.compat_config,
            evidence_config=args.evidence_config,
            workspace=workspace,
        )
        write_workspace_regression_config(
            base_config=args.base_config,
            output=args.output,
            output_dir_suffix=args.output_dir_suffix,
            source_template_id=args.source_template_id,
            workspace=workspace,
            knowledge_model_path=knowledge_model.path,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"INFO: Generated regression config for {workspace.version_tag} at {args.output}")


if __name__ == "__main__":
    main()
