#!/usr/bin/env python3
"""Run DSW regression for versions recommended by a compatibility plan."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dsw_document_template_tool.regression_config import (
    select_regression_knowledge_model,
    select_regression_workspace,
    write_workspace_regression_config,
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_RENDER_COMMAND = str(REPO_ROOT / ".venv" / "bin" / "dsw-template-render-regression")


@dataclass(frozen=True)
class PlannedRegression:
    """One regression run selected from the compatibility plan."""

    version: str
    reasons: tuple[str, ...]


def main() -> None:
    """Run all planned regression candidates for one DSW runtime."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument(
        "--compat-config",
        type=Path,
        default=REPO_ROOT / "config" / "dsw-compat.yml",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--generated-config-dir", type=Path, required=True)
    parser.add_argument(
        "--evidence-config",
        type=Path,
        default=REPO_ROOT / "config" / "regression-evidence.yml",
    )
    parser.add_argument("--metamodel-version", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--render-command", default=DEFAULT_RENDER_COMMAND)
    parser.add_argument("--source-template-id", required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    args = parser.parse_args()

    plan = _read_json(args.plan)
    planned_regressions = select_planned_regressions(
        plan=plan,
        metamodel_version=args.metamodel_version,
    )
    for planned in planned_regressions:
        run_planned_regression(
            base_config=args.base_config,
            compat_config=args.compat_config,
            dry_run=args.dry_run,
            generated_config_dir=args.generated_config_dir,
            evidence_config=args.evidence_config,
            metamodel_version=args.metamodel_version,
            planned=planned,
            render_command=args.render_command,
            source_template_id=args.source_template_id,
            workspace_root=args.workspace_root,
        )


def select_planned_regressions(
    *,
    plan: dict[str, Any],
    metamodel_version: str,
) -> list[PlannedRegression]:
    """Return recommended regression runs for one metamodel."""

    candidates = plan.get("candidates")
    if not isinstance(candidates, list):
        raise SystemExit("Regression plan has no `candidates` list")
    planned = [
        PlannedRegression(
            version=_required_str(candidate, "version"),
            reasons=tuple(_optional_str_list(candidate, "reasons")),
        )
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("recommended") is True
        and candidate.get("metamodel_version") == metamodel_version
    ]
    if planned:
        return planned
    raise SystemExit(
        f"Regression plan has no recommended candidate for metamodelVersion {metamodel_version!r}"
    )


def run_planned_regression(
    *,
    base_config: Path,
    compat_config: Path,
    dry_run: bool,
    generated_config_dir: Path,
    evidence_config: Path,
    metamodel_version: str,
    planned: PlannedRegression,
    render_command: str,
    source_template_id: str,
    workspace_root: Path,
) -> None:
    """Generate one versioned config and run the regression CLI."""

    workspace = select_regression_workspace(
        workspace_root=workspace_root,
        source_template_id=source_template_id,
        version=planned.version,
        metamodel_version=metamodel_version,
    )
    config_path = generated_config_dir / (
        f".generated-regression.ci.{_safe_path_part(metamodel_version)}.{workspace.version_tag}.yml"
    )
    knowledge_model = select_regression_knowledge_model(
        compat_config=compat_config,
        evidence_config=evidence_config,
        workspace=workspace,
    )
    write_workspace_regression_config(
        base_config=base_config,
        output=config_path,
        output_dir_suffix=workspace.version_tag,
        source_template_id=source_template_id,
        workspace=workspace,
        knowledge_model_path=knowledge_model.path,
    )
    reasons = ", ".join(planned.reasons) if planned.reasons else "planned"
    print(f"INFO: Running regression for {workspace.version_tag} ({reasons})", flush=True)
    if dry_run:
        print(f"INFO: Dry run; generated {config_path} and skipped DSW regression")
        return
    subprocess.run(
        [render_command, "--config", str(config_path)],
        check=True,
        env=_regression_env(),
    )


def _regression_env() -> dict[str, str]:
    env = dict(os.environ)
    api_port = env.get("DSW_CI_API_PORT", "3000")
    env.setdefault("DSW_API_URL", f"http://localhost:{api_port}/wizard-api")
    env.setdefault("DSW_DOWNLOAD_HOST_ALIAS", "host.docker.internal=localhost")
    env.setdefault("DSW_EMAIL", "albert.einstein@example.com")
    env.setdefault("DSW_PASSWORD", "password")
    return env


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object in {path}")
    return payload


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"Invalid regression plan candidate field {key!r}: {payload!r}")
    return value


def _optional_str_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"Invalid regression plan candidate field {key!r}: {payload!r}")
    return value


def _safe_path_part(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value).strip("-")


if __name__ == "__main__":
    main()
