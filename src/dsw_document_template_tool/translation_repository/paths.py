"""Branch and filesystem conventions for translated-template versions."""

from __future__ import annotations

from pathlib import Path

from .errors import TranslationRepositoryError
from .models import (
    CleanArtifactVersionPaths,
    TranslationRepositoryConfig,
    VersionWorkspacePaths,
)
from .policy import validate_supported_version
from .versions import sorted_versions, version_to_number


def version_branch(config: TranslationRepositoryConfig, version: str) -> str:
    """Return the translation branch name for a version tag."""

    validate_supported_version(config, version)
    return f"{config.branches.version_branch_prefix}{version}"


def migration_branch(config: TranslationRepositoryConfig, source: str, target: str) -> str:
    """Return the bot branch name for one source-to-target migration."""

    validate_supported_version(config, source)
    validate_supported_version(config, target)
    if source == target:
        raise TranslationRepositoryError("source and target versions must differ")
    return f"{config.migration.auto_pr_branch_prefix}-{source}-to-{target}"


def version_paths(config: TranslationRepositoryConfig, version: str) -> VersionWorkspacePaths:
    """Return conventional workspace/output paths for one version."""

    validate_supported_version(config, version)
    version_number = version_to_number(version)
    source_template_id = f"{config.template.organization_id}-{config.template.template_id}"
    workspace_template_name = f"{source_template_id}-{version_number}"
    translated_workspace_name = (
        f"{config.translation.translated_template_organization_id}-"
        f"{config.translation.translated_template_id}-{version_number}"
    )
    output_root = (
        Path("outputs")
        / "document-templates"
        / source_template_id
        / version
        / config.translation.target_language_label
    )
    project_render_output = (
        Path("outputs")
        / "project-render"
        / source_template_id
        / version
        / config.translation.target_language_label
        / "test-project.pdf"
    )
    return VersionWorkspacePaths(
        version=version,
        version_number=version_number,
        source_template_id=source_template_id,
        workspace_template_name=workspace_template_name,
        compact_template_dir=Path("workspace")
        / "document-templates"
        / "compact"
        / workspace_template_name,
        expanded_template_dir=Path("workspace")
        / "document-templates"
        / "expanded"
        / workspace_template_name,
        translation_tree_dir=Path("workspace")
        / "document-templates"
        / "translation"
        / workspace_template_name,
        xliff_exchange_path=config.xliff_exchange.path,
        project_render_output=project_render_output,
        translated_template_dir=output_root / translated_workspace_name,
        translated_template_package=output_root / f"{translated_workspace_name}.zip",
        migration_report_dir=Path("migration-reports"),
    )


def clean_artifact_version_paths(
    config: TranslationRepositoryConfig,
    version: str,
    artifact_root: Path,
) -> CleanArtifactVersionPaths:
    """Return clean scaffold paths for one version inside a downloaded artifact."""

    paths = version_paths(config, version)
    workspace_root = (
        Path(artifact_root) / "upstream-workspaces" / paths.source_template_id / version
    )
    return CleanArtifactVersionPaths(
        version=version,
        compact_template_dir=workspace_root / "compact" / paths.workspace_template_name,
        expanded_template_dir=workspace_root / "expanded" / paths.workspace_template_name,
        translation_tree_dir=workspace_root / "translation" / paths.workspace_template_name,
    )


def clean_artifact_versions(
    *,
    config: TranslationRepositoryConfig,
    artifact_root: Path,
) -> list[str]:
    """Return template versions available in a downloaded clean scaffold artifact."""

    source_template_id = f"{config.template.organization_id}-{config.template.template_id}"
    workspace_root = Path(artifact_root) / "upstream-workspaces" / source_template_id
    if not workspace_root.is_dir():
        return []
    versions = [
        path.name
        for path in workspace_root.iterdir()
        if path.is_dir() and path.name.startswith("v")
    ]
    return sorted_versions(versions)
