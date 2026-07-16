#!/usr/bin/env python3
"""Generate a version-aware regression config from built upstream workspaces."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from dsw_document_template_tool.regression_evidence import (
    KnowledgeModelEvidence,
    load_regression_evidence_config,
    validate_regression_evidence_config,
)
from dsw_document_template_tool.translation_repository import (
    load_preview_runtimes,
    preview_runtime_for_template,
)
from dsw_document_template_tool.yaml_config import YamlConfigError, load_yaml_file

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from resolve_upstream_refs import parse_version_tag  # noqa: E402


@dataclass(frozen=True)
class RegressionWorkspace:
    """One built upstream workspace that can be used for full regression."""

    version: str
    version_tag: str
    metamodel_version: str
    compact_dir: Path
    expanded_regression_dir: Path


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
    write_regression_config(
        base_config=args.base_config,
        output=args.output,
        output_dir_suffix=args.output_dir_suffix,
        source_template_id=args.source_template_id,
        workspace=workspace,
        knowledge_model_path=knowledge_model.path,
    )
    print(f"INFO: Generated regression config for {workspace.version_tag} at {args.output}")


def select_regression_workspace(
    *,
    workspace_root: Path,
    source_template_id: str,
    version: str,
    metamodel_version: str,
) -> RegressionWorkspace:
    """Select the latest or explicitly requested workspace for regression."""

    workspaces = discover_regression_workspaces(
        workspace_root=workspace_root,
        source_template_id=source_template_id,
        metamodel_version=metamodel_version,
    )
    if version == "latest":
        if not workspaces:
            raise SystemExit(_missing_workspace_message(workspace_root, metamodel_version))
        return workspaces[-1]

    requested_tag = version if version.startswith("v") else f"v{version}"
    for workspace in workspaces:
        if workspace.version_tag == requested_tag:
            return workspace
    raise SystemExit(
        f"No regression workspace found for {requested_tag} under {workspace_root}. "
        "Run make build-upstream-artifacts first."
    )


def discover_regression_workspaces(
    *,
    workspace_root: Path,
    source_template_id: str,
    metamodel_version: str,
) -> list[RegressionWorkspace]:
    """Return built regression workspaces sorted by semantic version."""

    workspaces: list[RegressionWorkspace] = []
    for version_dir in sorted(workspace_root.glob("v*")):
        if not version_dir.is_dir() or parse_version_tag(version_dir.name) is None:
            continue
        version = version_dir.name.removeprefix("v")
        template_name = f"{source_template_id}-{version}"
        compact_dir = version_dir / "compact" / template_name
        expanded_regression_dir = version_dir / "expanded-regression" / template_name
        template_json = compact_dir / "template.json"
        if not template_json.is_file() or not expanded_regression_dir.is_dir():
            continue

        payload = json.loads(template_json.read_text(encoding="utf-8"))
        workspace_metamodel = str(payload.get("metamodelVersion", ""))
        if metamodel_version and workspace_metamodel != metamodel_version:
            continue
        workspaces.append(
            RegressionWorkspace(
                version=version,
                version_tag=version_dir.name,
                metamodel_version=workspace_metamodel,
                compact_dir=compact_dir,
                expanded_regression_dir=expanded_regression_dir,
            )
        )
    return sorted(workspaces, key=lambda item: parse_version_tag(item.version_tag) or (-1, -1, -1))


def write_regression_config(
    *,
    base_config: Path,
    output: Path,
    output_dir_suffix: str = "",
    source_template_id: str,
    workspace: RegressionWorkspace,
    knowledge_model_path: Path | None = None,
) -> None:
    """Write a config whose subjects point at the selected workspace."""

    try:
        payload = load_yaml_file(base_config) or {}
    except YamlConfigError as exc:
        raise SystemExit(str(exc)) from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected mapping root in {base_config}")
    subjects = payload.setdefault("subjects", {})
    if not isinstance(subjects, dict):
        raise SystemExit(f"Expected `subjects` mapping in {base_config}")

    stage_template_id = source_template_id.removeprefix("dsw-")
    subjects["baseline"] = {
        "kind": "local_dir",
        "value": _relative_posix_path(workspace.compact_dir, output.parent),
        "stage_id": f"ci:{stage_template_id}-compact:{workspace.version}",
    }
    subjects["candidate"] = {
        "kind": "local_dir",
        "value": _relative_posix_path(workspace.expanded_regression_dir, output.parent),
        "stage_id": f"ci:{stage_template_id}-expanded:{workspace.version}",
    }
    if knowledge_model_path is not None:
        set_regression_knowledge_model(
            payload,
            path=_relative_posix_path(knowledge_model_path, output.parent),
        )
    if output_dir_suffix:
        append_regression_output_dir_suffix(payload, suffix=output_dir_suffix)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def select_regression_knowledge_model(
    *,
    compat_config: Path,
    evidence_config: Path,
    workspace: RegressionWorkspace,
) -> KnowledgeModelEvidence:
    """Return verified KM evidence for a selected template workspace."""

    runtimes = load_preview_runtimes(compat_config)
    evidence = load_regression_evidence_config(evidence_config)
    validate_regression_evidence_config(evidence, runtimes)
    runtime = preview_runtime_for_template(
        workspace.version_tag,
        workspace.metamodel_version,
        runtimes=runtimes,
    )
    return evidence.knowledge_model_for_runtime(runtime)


def set_regression_knowledge_model(payload: dict[str, object], *, path: str) -> None:
    """Set one verified KM bundle on each fixture that creates a project."""

    for section_name in ("fixtures", "generated_fixtures"):
        fixtures = payload.get(section_name, [])
        if not isinstance(fixtures, list):
            raise SystemExit(f"Expected `{section_name}` list in base config")
        for fixture in fixtures:
            if not isinstance(fixture, dict):
                raise SystemExit(f"Expected mappings in `{section_name}`")
            project = fixture.get("project")
            if project is None:
                continue
            if not isinstance(project, dict):
                raise SystemExit(f"Expected `{section_name}.project` mapping in base config")
            project["knowledge_model_package_id"] = path


def append_regression_output_dir_suffix(payload: dict[str, object], *, suffix: str) -> None:
    """Append a stable suffix to the regression output directory."""

    regression = payload.setdefault("regression", {})
    if not isinstance(regression, dict):
        raise SystemExit("Expected `regression` mapping in base config")
    output_dir = regression.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise SystemExit("Expected `regression.output_dir` string in base config")
    regression["output_dir"] = f"{output_dir.rstrip('/')}/{suffix.strip('/')}"


def _relative_posix_path(path: Path, base_dir: Path) -> str:
    return Path(os.path.relpath(path, start=base_dir)).as_posix()


def _missing_workspace_message(workspace_root: Path, metamodel_version: str) -> str:
    metamodel_hint = f" for metamodel {metamodel_version}" if metamodel_version else ""
    return (
        f"No built regression workspaces{metamodel_hint} found under {workspace_root}. "
        "Run make build-upstream-artifacts first."
    )


if __name__ == "__main__":
    main()
