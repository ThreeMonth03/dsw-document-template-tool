"""Generate version-aware configs for comparison and package render regression."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .regression_evidence import (
    KnowledgeModelEvidence,
    load_regression_evidence_config,
    validate_regression_evidence_config,
)
from .translation_repository import (
    DswPreviewRuntime,
    TranslationRepositoryError,
    load_preview_runtimes,
    preview_runtime_for_template,
    version_sort_key,
)
from .yaml_config import YamlConfigError, load_yaml_file


@dataclass(frozen=True)
class RegressionWorkspace:
    """One built upstream workspace that can be used for full regression."""

    version: str
    version_tag: str
    metamodel_version: str
    compact_dir: Path
    expanded_regression_dir: Path


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
            raise ValueError(_missing_workspace_message(workspace_root, metamodel_version))
        return workspaces[-1]

    requested_tag = version if version.startswith("v") else f"v{version}"
    for workspace in workspaces:
        if workspace.version_tag == requested_tag:
            return workspace
    raise ValueError(
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
        if not version_dir.is_dir() or not _is_version_tag(version_dir.name):
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
    return sorted(workspaces, key=lambda item: version_sort_key(item.version_tag))


def write_workspace_regression_config(
    *,
    base_config: Path,
    output: Path,
    output_dir_suffix: str,
    source_template_id: str,
    workspace: RegressionWorkspace,
    knowledge_model_path: Path,
) -> None:
    """Write an equality config for one compact/expanded upstream pair."""

    payload = _load_base_config(base_config)
    stage_template_id = source_template_id.removeprefix("dsw-")
    payload["subjects"] = {
        "baseline": {
            "kind": "local_dir",
            "value": _relative_posix_path(workspace.compact_dir, output.parent),
            "stage_id": f"ci:{stage_template_id}-compact:{workspace.version}",
        },
        "candidate": {
            "kind": "local_dir",
            "value": _relative_posix_path(
                workspace.expanded_regression_dir,
                output.parent,
            ),
            "stage_id": f"ci:{stage_template_id}-expanded:{workspace.version}",
        },
    }
    regression = _regression_section(payload)
    regression["assertion"] = "equal"
    regression["mode"] = "preview"
    if output_dir_suffix:
        _append_regression_output_dir_suffix(payload, suffix=output_dir_suffix)
    _set_regression_knowledge_model(
        payload,
        path=_relative_posix_path(knowledge_model_path, output.parent),
    )
    _write_config(payload, output)


def write_package_render_config(
    *,
    base_config: Path,
    output: Path,
    output_dir: Path,
    package_path: Path,
    knowledge_model_path: Path,
) -> None:
    """Write a single-subject full render config for one packaged template."""

    package_path = package_path.resolve()
    if not package_path.is_file():
        raise ValueError(f"Translated template package does not exist: {package_path}")
    payload = _load_base_config(base_config)
    payload["subjects"] = {
        "candidate": {
            "kind": "local_package",
            "value": _relative_posix_path(package_path, output.parent),
        }
    }
    regression = _regression_section(payload)
    regression["assertion"] = "render_success"
    regression["mode"] = "document"
    regression["output_dir"] = _relative_posix_path(output_dir.resolve(), output.parent)
    _set_regression_knowledge_model(
        payload,
        path=_relative_posix_path(knowledge_model_path, output.parent),
    )
    _write_config(payload, output)


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


def select_regression_knowledge_model_for_metamodel(
    *,
    compat_config: Path,
    evidence_config: Path,
    metamodel_version: str,
) -> KnowledgeModelEvidence:
    """Return verified KM evidence for one configured document-template metamodel."""

    runtimes = load_preview_runtimes(compat_config)
    evidence = load_regression_evidence_config(evidence_config)
    validate_regression_evidence_config(evidence, runtimes)
    runtime = _runtime_for_metamodel(runtimes, metamodel_version)
    return evidence.knowledge_model_for_runtime(runtime)


def _runtime_for_metamodel(
    runtimes: tuple[DswPreviewRuntime, ...],
    metamodel_version: str,
) -> DswPreviewRuntime:
    matches = [runtime for runtime in runtimes if runtime.metamodel_version == metamodel_version]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one runtime for metamodel {metamodel_version}, found {len(matches)}"
        )
    return matches[0]


def _load_base_config(path: Path) -> dict[str, object]:
    try:
        payload = load_yaml_file(path) or {}
    except YamlConfigError as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping root in {path}")
    return payload


def _regression_section(payload: dict[str, object]) -> dict[str, object]:
    regression = payload.setdefault("regression", {})
    if not isinstance(regression, dict):
        raise ValueError("Expected `regression` mapping in base config")
    return regression


def _set_regression_knowledge_model(payload: dict[str, object], *, path: str) -> None:
    for section_name in ("fixtures", "generated_fixtures"):
        fixtures = payload.get(section_name, [])
        if not isinstance(fixtures, list):
            raise ValueError(f"Expected `{section_name}` list in base config")
        for fixture in fixtures:
            if not isinstance(fixture, dict):
                raise ValueError(f"Expected mappings in `{section_name}`")
            project = fixture.get("project")
            if project is None:
                continue
            if not isinstance(project, dict):
                raise ValueError(f"Expected `{section_name}.project` mapping in base config")
            project["knowledge_model_package_id"] = path


def _append_regression_output_dir_suffix(payload: dict[str, object], *, suffix: str) -> None:
    regression = _regression_section(payload)
    output_dir = regression.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("Expected `regression.output_dir` string in base config")
    regression["output_dir"] = f"{output_dir.rstrip('/')}/{suffix.strip('/')}"


def _write_config(payload: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _relative_posix_path(path: Path, base_dir: Path) -> str:
    return Path(os.path.relpath(path, start=base_dir)).as_posix()


def _missing_workspace_message(workspace_root: Path, metamodel_version: str) -> str:
    metamodel_hint = f" for metamodel {metamodel_version}" if metamodel_version else ""
    return (
        f"No built regression workspaces{metamodel_hint} found under {workspace_root}. "
        "Run make build-upstream-artifacts first."
    )


def _is_version_tag(value: str) -> bool:
    try:
        version_sort_key(value)
    except TranslationRepositoryError:
        return False
    return True
