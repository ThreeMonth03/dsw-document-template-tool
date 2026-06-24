"""Helpers for cross-version document-template translation migration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class TranslationMigrationError(RuntimeError):
    """Raised when translation migration configuration is invalid."""


@dataclass(frozen=True)
class TemplateConfig:
    """Source template coordinates and upstream version policy."""

    organization_id: str
    template_id: str
    upstream_repository: str
    supported_ref_spec: str
    supported_versions: tuple[str, ...]


@dataclass(frozen=True)
class TranslationConfig:
    """Target translation metadata."""

    source_language: str
    target_language: str
    target_language_label: str
    translated_template_organization_id: str
    translated_template_id: str
    translated_template_name: str


@dataclass(frozen=True)
class BranchConfig:
    """Translation repository branch naming policy."""

    version_branch_prefix: str


@dataclass(frozen=True)
class MigrationConfig:
    """Cross-version migration policy."""

    mode: str
    non_exact_policy: str
    auto_pr_enabled: bool
    auto_pr_branch_prefix: str
    auto_merge_when_clean: bool


@dataclass(frozen=True)
class ToolingConfig:
    """Tooling repository reference used by downstream workflows."""

    repository: str
    ref: str


@dataclass(frozen=True)
class TranslationRepositoryConfig:
    """Parsed translation repository configuration."""

    template: TemplateConfig
    translation: TranslationConfig
    branches: BranchConfig
    migration: MigrationConfig
    tooling: ToolingConfig


@dataclass(frozen=True)
class VersionWorkspacePaths:
    """Conventional paths for one translated template version branch."""

    version: str
    version_number: str
    source_template_id: str
    workspace_template_name: str
    compact_template_dir: Path
    expanded_template_dir: Path
    translation_tree_dir: Path
    translated_template_dir: Path
    translated_template_package: Path
    migration_report_dir: Path


@dataclass(frozen=True)
class CleanArtifactVersionPaths:
    """Conventional paths for one clean upstream scaffold artifact."""

    version: str
    compact_template_dir: Path
    expanded_template_dir: Path
    translation_tree_dir: Path


@dataclass(frozen=True)
class DswPreviewRuntime:
    """DSW runtime that can preview a template metamodel range."""

    metamodel_key: str
    metamodel_version: str
    dsw_version: str
    tdk_version: str
    min_version: str
    max_version: str | None
    upstream_template_artifact_refs: str
    run_preview_regression: bool
    strict_project_preview: bool


DEFAULT_DSW_COMPAT_PATH = Path(__file__).resolve().parents[2] / "config" / "dsw-compat.yml"
DSW_PREVIEW_RUNTIMES: tuple[DswPreviewRuntime, ...] = ()


def load_preview_runtimes(
    path: Path | None = None,
) -> tuple[DswPreviewRuntime, ...]:
    """Load DSW preview runtimes from the checked-in compatibility table."""

    config_path = path or DEFAULT_DSW_COMPAT_PATH
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TranslationMigrationError(
            f"DSW compatibility config {config_path} must contain a mapping"
        )

    runtime_payloads = payload.get("runtimes")
    if not isinstance(runtime_payloads, list) or not runtime_payloads:
        raise TranslationMigrationError(
            f"DSW compatibility config {config_path} must define non-empty runtimes"
        )

    runtimes = tuple(_load_preview_runtime(item) for item in runtime_payloads)
    _validate_preview_runtimes(runtimes)
    return runtimes


def _load_preview_runtime(payload: object) -> DswPreviewRuntime:
    if not isinstance(payload, dict):
        raise TranslationMigrationError("Each DSW preview runtime must be a mapping")
    max_version = payload.get("max_version")
    if max_version is not None and not isinstance(max_version, str):
        raise TranslationMigrationError("Expected string or null at max_version")
    return DswPreviewRuntime(
        metamodel_key=_required_str(payload, "metamodel_key"),
        metamodel_version=_required_str(payload, "metamodel_version"),
        dsw_version=_required_str(payload, "dsw_version"),
        tdk_version=_required_str(payload, "tdk_version"),
        min_version=_required_str(payload, "min_version"),
        max_version=max_version,
        upstream_template_artifact_refs=_required_str(
            payload,
            "upstream_template_artifact_refs",
        ),
        run_preview_regression=bool(payload.get("run_preview_regression", False)),
        strict_project_preview=bool(payload.get("strict_project_preview", False)),
    )


def _validate_preview_runtimes(runtimes: tuple[DswPreviewRuntime, ...]) -> None:
    seen_keys: set[str] = set()
    seen_metamodels: set[str] = set()
    for runtime in runtimes:
        if runtime.metamodel_key in seen_keys:
            raise TranslationMigrationError(
                f"Duplicate DSW preview runtime key {runtime.metamodel_key!r}"
            )
        seen_keys.add(runtime.metamodel_key)
        if runtime.metamodel_version in seen_metamodels:
            raise TranslationMigrationError(
                "Each metamodelVersion should map to one CI runtime; "
                f"duplicate {runtime.metamodel_version!r}"
            )
        seen_metamodels.add(runtime.metamodel_version)
        if runtime.max_version is not None and (
            version_sort_key(runtime.max_version) < version_sort_key(runtime.min_version)
        ):
            raise TranslationMigrationError(
                f"Runtime {runtime.metamodel_key} has max_version before min_version"
            )


def load_translation_repository_config(path: Path) -> TranslationRepositoryConfig:
    """Load and validate ``translation-config.yml``."""

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TranslationMigrationError("translation-config.yml must contain a mapping")

    try:
        template_payload = payload["template"]
        translation_payload = payload["translation"]
        branch_payload = payload["branches"]
        tooling_payload = payload["tooling"]
        migration_payload = payload["migration"]
    except KeyError as exc:
        raise TranslationMigrationError(
            f"translation-config.yml is missing top-level key {exc.args[0]!r}"
        ) from exc

    template = TemplateConfig(
        organization_id=_required_str(template_payload, "organization_id"),
        template_id=_required_str(template_payload, "template_id"),
        upstream_repository=_required_str(template_payload, "upstream_repository"),
        supported_ref_spec=str(template_payload.get("supported_ref_spec", "")),
        supported_versions=tuple(_required_str_list(template_payload, "supported_versions")),
    )
    translation = TranslationConfig(
        source_language=_required_str(translation_payload, "source_language"),
        target_language=_required_str(translation_payload, "target_language"),
        target_language_label=_required_str(translation_payload, "target_language_label"),
        translated_template_organization_id=_required_str(
            translation_payload,
            "translated_template_organization_id",
        ),
        translated_template_id=_required_str(
            translation_payload,
            "translated_template_id",
        ),
        translated_template_name=_required_str(
            translation_payload,
            "translated_template_name",
        ),
    )
    branches = BranchConfig(
        version_branch_prefix=_required_str(branch_payload, "version_branch_prefix"),
    )
    tooling = ToolingConfig(
        repository=_required_str(tooling_payload, "repository"),
        ref=_required_str(tooling_payload, "ref"),
    )
    migration = MigrationConfig(
        mode=_required_str(migration_payload, "mode"),
        non_exact_policy=_required_str(migration_payload, "non_exact_policy"),
        auto_pr_enabled=bool(migration_payload.get("auto_pr_enabled", False)),
        auto_pr_branch_prefix=str(
            migration_payload.get("auto_pr_branch_prefix", "automation/migrate")
        ),
        auto_merge_when_clean=bool(migration_payload.get("auto_merge_when_clean", False)),
    )

    if not template.supported_versions:
        raise TranslationMigrationError("template.supported_versions must not be empty")
    if migration.mode != "exact-only":
        raise TranslationMigrationError("Only exact-only migration is currently supported")

    return TranslationRepositoryConfig(
        template=template,
        translation=translation,
        branches=branches,
        migration=migration,
        tooling=tooling,
    )


def version_branch(config: TranslationRepositoryConfig, version: str) -> str:
    """Return the translation branch name for a version tag."""

    validate_supported_version(config, version)
    return f"{config.branches.version_branch_prefix}{version}"


def migration_branch(config: TranslationRepositoryConfig, source: str, target: str) -> str:
    """Return the bot branch name for one source-to-target migration."""

    validate_supported_version(config, source)
    validate_supported_version(config, target)
    if source == target:
        raise TranslationMigrationError("source and target versions must differ")
    return f"{config.migration.auto_pr_branch_prefix}-{source}-to-{target}"


def target_versions(
    config: TranslationRepositoryConfig,
    source_version: str,
    requested_targets: list[str] | None = None,
) -> list[str]:
    """Return supported target versions for one source version."""

    validate_supported_version(config, source_version)
    if requested_targets:
        for version in requested_targets:
            validate_supported_version(config, version)
        versions = requested_targets
    else:
        versions = list(config.template.supported_versions)
    return [version for version in versions if version != source_version]


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


def preview_runtime_for_version(version: str) -> DswPreviewRuntime:
    """Return the DSW runtime that can preview a template version tag."""

    for runtime in DSW_PREVIEW_RUNTIMES:
        if _version_in_runtime(version, runtime):
            return runtime
    raise TranslationMigrationError(
        f"No DSW preview runtime configured for template version {version!r}"
    )


def preview_runtime_for_template(version: str, metamodel_version: str) -> DswPreviewRuntime:
    """Return the configured runtime for a concrete template version/metamodel pair."""

    runtime = preview_runtime_for_version(version)
    if runtime.metamodel_version != metamodel_version:
        raise TranslationMigrationError(
            f"Template {version} uses metamodelVersion {metamodel_version!r}, but "
            f"configured runtime {runtime.metamodel_key!r} expects "
            f"{runtime.metamodel_version!r}"
        )
    return runtime


def preview_runtime_matrix() -> list[dict[str, str]]:
    """Return GitHub Actions matrix rows for all configured preview runtimes."""

    return [
        {
            "metamodel_key": runtime.metamodel_key,
            "metamodel_version": runtime.metamodel_version,
            "dsw_version": runtime.dsw_version,
            "tdk_version": runtime.tdk_version,
            "upstream_template_artifact_refs": runtime.upstream_template_artifact_refs,
            "run_preview_regression": str(runtime.run_preview_regression).lower(),
            "strict_project_preview": str(runtime.strict_project_preview).lower(),
        }
        for runtime in DSW_PREVIEW_RUNTIMES
    ]


def sorted_versions(versions: list[str] | tuple[str, ...]) -> list[str]:
    """Sort version tags using numeric semantic version ordering."""

    return sorted(versions, key=version_sort_key)


def version_sort_key(version: str) -> tuple[int, ...]:
    """Return a sortable key for version tags such as ``v1.30.1``."""

    version_number = version_to_number(version)
    parts = version_number.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        raise TranslationMigrationError(f"Expected numeric version tag, got {version!r}")
    return tuple(int(part) for part in parts)


def version_to_number(version: str) -> str:
    """Convert ``v1.30.1`` to ``1.30.1``."""

    if not version.startswith("v") or len(version) == 1:
        raise TranslationMigrationError(f"Expected a version tag like v1.30.1, got {version!r}")
    return version[1:]


def validate_supported_version(config: TranslationRepositoryConfig, version: str) -> None:
    """Raise if a version is not configured as supported."""

    if version not in config.template.supported_versions:
        supported = ", ".join(config.template.supported_versions)
        raise TranslationMigrationError(
            f"Unsupported version {version!r}. Supported versions: {supported}"
        )


def _version_in_runtime(version: str, runtime: DswPreviewRuntime) -> bool:
    version_key = version_sort_key(version)
    if version_key < version_sort_key(runtime.min_version):
        return False
    return runtime.max_version is None or version_key <= version_sort_key(runtime.max_version)


def _required_str(payload: object, key: str) -> str:
    if not isinstance(payload, dict):
        raise TranslationMigrationError(f"Expected mapping while reading {key!r}")
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise TranslationMigrationError(f"Expected non-empty string at {key!r}")
    return value


def _required_str_list(payload: object, key: str) -> list[str]:
    if not isinstance(payload, dict):
        raise TranslationMigrationError(f"Expected mapping while reading {key!r}")
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise TranslationMigrationError(f"Expected non-empty string list at {key!r}")
    return value


DSW_PREVIEW_RUNTIMES = load_preview_runtimes()
