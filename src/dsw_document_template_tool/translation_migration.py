"""Helpers for cross-version document-template translation migration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from .yaml_config import YamlConfigError, load_yaml_file


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
    translated_template_description: str | None
    translated_template_id: str
    translated_template_name: str


@dataclass(frozen=True)
class BranchConfig:
    """Translation repository branch naming policy."""

    control_branch: str
    version_branch_prefix: str


@dataclass(frozen=True)
class XliffExchangeConfig:
    """Optional branch-local XLIFF exchange policy."""

    enabled: bool
    path: Path


@dataclass(frozen=True)
class MigrationConfig:
    """Cross-version migration policy."""

    mode: str
    non_exact_policy: str
    auto_pr_enabled: bool
    auto_pr_branch_prefix: str
    auto_merge_when_clean: bool


VersionRefreshPolicy = Literal["artifact", "manual", "false"]
VersionMigrationPolicy = Literal["auto", "manual", "false"]
VersionLifecycleState = Literal["available", "active", "maintenance", "published", "archived"]
VERSION_LIFECYCLE_STATES: tuple[VersionLifecycleState, ...] = (
    "available",
    "active",
    "maintenance",
    "published",
    "archived",
)


@dataclass(frozen=True)
class VersionPolicyValues:
    """Operational policy values applied to one template version."""

    state: VersionLifecycleState
    refresh: VersionRefreshPolicy
    migrate_into: VersionMigrationPolicy
    publish_release: bool
    reason: str


@dataclass(frozen=True)
class VersionPolicyPatch:
    """Fields explicitly supplied by one rule or exact override."""

    state: VersionLifecycleState | None = None
    refresh: VersionRefreshPolicy | None = None
    migrate_into: VersionMigrationPolicy | None = None
    publish_release: bool | None = None
    reason: str | None = None


@dataclass(frozen=True)
class VersionPolicyRule:
    """Range-based version policy rule."""

    match: str
    values: VersionPolicyPatch


@dataclass(frozen=True)
class VersionPolicyConfig:
    """Version lifecycle policy loaded from ``translation-config.yml``."""

    defaults: VersionPolicyValues
    rules: tuple[VersionPolicyRule, ...]
    overrides: dict[str, VersionPolicyPatch]


@dataclass(frozen=True)
class PublicReadmeConfig:
    """User-facing README copied into generated translated templates."""

    path: Path


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
    public_readme: PublicReadmeConfig
    tooling: ToolingConfig
    version_policy: VersionPolicyConfig
    xliff_exchange: XliffExchangeConfig


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
    xliff_exchange_path: Path
    project_render_output: Path
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
DSW_COMPAT_SCHEMA_VERSION = 1
DSW_PREVIEW_RUNTIMES: tuple[DswPreviewRuntime, ...]
TRANSLATION_CONFIG_SCHEMA_VERSION = 2


def load_preview_runtimes(
    path: Path | None = None,
) -> tuple[DswPreviewRuntime, ...]:
    """Load DSW preview runtimes from the checked-in compatibility table."""

    config_path = path or DEFAULT_DSW_COMPAT_PATH
    try:
        payload = load_yaml_file(config_path)
    except YamlConfigError as exc:
        raise TranslationMigrationError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise TranslationMigrationError(
            f"DSW compatibility config {config_path} must contain a mapping"
        )
    _reject_unknown_keys(payload, {"runtimes", "schema_version"}, "DSW compatibility config")
    if payload.get("schema_version") != DSW_COMPAT_SCHEMA_VERSION:
        raise TranslationMigrationError(
            f"DSW compatibility config schema_version must be {DSW_COMPAT_SCHEMA_VERSION}"
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
    _reject_unknown_keys(
        payload,
        {
            "dsw_version",
            "max_version",
            "metamodel_key",
            "metamodel_version",
            "min_version",
            "run_preview_regression",
            "strict_project_preview",
            "tdk_version",
            "upstream_template_artifact_refs",
        },
        "DSW preview runtime",
    )
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
        run_preview_regression=_optional_bool(
            payload,
            "run_preview_regression",
            default=False,
        ),
        strict_project_preview=_optional_bool(
            payload,
            "strict_project_preview",
            default=False,
        ),
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
        version_sort_key(runtime.min_version)
        if runtime.max_version is not None and (
            version_sort_key(runtime.max_version) < version_sort_key(runtime.min_version)
        ):
            raise TranslationMigrationError(
                f"Runtime {runtime.metamodel_key} has max_version before min_version"
            )


def load_translation_repository_config(path: Path) -> TranslationRepositoryConfig:
    """Load and validate ``translation-config.yml``."""

    try:
        payload = load_yaml_file(path)
    except YamlConfigError as exc:
        raise TranslationMigrationError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise TranslationMigrationError("translation-config.yml must contain a mapping")

    _reject_unknown_keys(
        payload,
        {
            "branches",
            "migration",
            "public_readme",
            "schema_version",
            "template",
            "tooling",
            "translation",
            "version_policy",
            "xliff_exchange",
        },
        "translation-config.yml",
    )
    if payload.get("schema_version") != TRANSLATION_CONFIG_SCHEMA_VERSION:
        raise TranslationMigrationError(
            f"translation-config.yml schema_version must be {TRANSLATION_CONFIG_SCHEMA_VERSION}"
        )

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

    _reject_unknown_keys(
        template_payload,
        {
            "organization_id",
            "supported_ref_spec",
            "supported_versions",
            "template_id",
            "upstream_repository",
        },
        "template",
    )
    _reject_unknown_keys(
        translation_payload,
        {
            "source_language",
            "target_language",
            "target_language_label",
            "translated_template_description",
            "translated_template_id",
            "translated_template_name",
            "translated_template_organization_id",
        },
        "translation",
    )
    _reject_unknown_keys(
        branch_payload,
        {"control_branch", "version_branch_prefix"},
        "branches",
    )
    _reject_unknown_keys(tooling_payload, {"ref", "repository"}, "tooling")
    _reject_unknown_keys(
        migration_payload,
        {
            "auto_merge_when_clean",
            "auto_pr_branch_prefix",
            "auto_pr_enabled",
            "mode",
            "non_exact_policy",
        },
        "migration",
    )

    template = TemplateConfig(
        organization_id=_required_str(template_payload, "organization_id"),
        template_id=_required_str(template_payload, "template_id"),
        upstream_repository=_required_str(template_payload, "upstream_repository"),
        supported_ref_spec=_optional_str(template_payload, "supported_ref_spec"),
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
        translated_template_description=_optional_str(
            translation_payload,
            "translated_template_description",
            default=None,
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
        control_branch=_optional_str(branch_payload, "control_branch", default="master"),
        version_branch_prefix=_required_str(branch_payload, "version_branch_prefix"),
    )
    tooling = ToolingConfig(
        repository=_required_str(tooling_payload, "repository"),
        ref=_required_str(tooling_payload, "ref"),
    )
    migration = MigrationConfig(
        mode=_required_str(migration_payload, "mode"),
        non_exact_policy=_required_str(migration_payload, "non_exact_policy"),
        auto_pr_enabled=_optional_bool(migration_payload, "auto_pr_enabled", default=False),
        auto_pr_branch_prefix=_optional_str(
            migration_payload,
            "auto_pr_branch_prefix",
            default="automation/migrate",
        ),
        auto_merge_when_clean=_optional_bool(
            migration_payload,
            "auto_merge_when_clean",
            default=False,
        ),
    )
    xliff_exchange_payload = payload.get("xliff_exchange", {})
    if xliff_exchange_payload is None:
        xliff_exchange_payload = {}
    if not isinstance(xliff_exchange_payload, dict):
        raise TranslationMigrationError("translation-config.yml xliff_exchange must be a mapping")
    _reject_unknown_keys(xliff_exchange_payload, {"enabled", "path"}, "xliff_exchange")
    source_template_id = f"{template.organization_id}-{template.template_id}"
    xliff_exchange = XliffExchangeConfig(
        enabled=_optional_bool(xliff_exchange_payload, "enabled", default=False),
        path=Path(
            _optional_str(
                xliff_exchange_payload,
                "path",
                default=(f"xliff/{source_template_id}.{translation.target_language}.xlf"),
            )
        ),
    )
    public_readme_payload = payload.get("public_readme", {})
    if public_readme_payload is None:
        public_readme_payload = {}
    if not isinstance(public_readme_payload, dict):
        raise TranslationMigrationError("translation-config.yml public_readme must be a mapping")
    _reject_unknown_keys(public_readme_payload, {"path"}, "public_readme")
    public_readme = PublicReadmeConfig(
        path=Path(
            _optional_str(
                public_readme_payload,
                "path",
                default="workspace/document-templates/public-readme/README.md",
            )
        ),
    )
    version_policy = _load_version_policy(payload.get("version_policy", {}))

    if not template.supported_versions:
        raise TranslationMigrationError("template.supported_versions must not be empty")
    duplicate_versions = _duplicate_items(template.supported_versions)
    if duplicate_versions:
        duplicates = ", ".join(duplicate_versions)
        raise TranslationMigrationError(
            f"template.supported_versions contains duplicate entries: {duplicates}"
        )
    for version in template.supported_versions:
        version_sort_key(version)
    if migration.mode != "exact-only":
        raise TranslationMigrationError("Only exact-only migration is currently supported")
    if migration.non_exact_policy != "leave_empty_needs_translation":
        raise TranslationMigrationError(
            "Only leave_empty_needs_translation non-exact migration policy is currently supported"
        )
    if not migration.auto_pr_branch_prefix:
        raise TranslationMigrationError("migration.auto_pr_branch_prefix must not be empty")
    if not branches.control_branch:
        raise TranslationMigrationError("branches.control_branch must not be empty")
    if not branches.version_branch_prefix:
        raise TranslationMigrationError("branches.version_branch_prefix must not be empty")
    if public_readme.path.is_absolute() or ".." in public_readme.path.parts:
        raise TranslationMigrationError("public_readme.path must be a repo-relative path")
    if xliff_exchange.path.is_absolute() or ".." in xliff_exchange.path.parts:
        raise TranslationMigrationError("xliff_exchange.path must be a repo-relative path")

    config = TranslationRepositoryConfig(
        template=template,
        translation=translation,
        branches=branches,
        migration=migration,
        public_readme=public_readme,
        tooling=tooling,
        version_policy=version_policy,
        xliff_exchange=xliff_exchange,
    )
    _validate_version_lifecycle_policy(config)
    return config


def _validate_version_lifecycle_policy(config: TranslationRepositoryConfig) -> None:
    """Reject lifecycle policies that could mutate frozen versions."""

    frozen_states = {"published", "archived"}
    for version in config.template.supported_versions:
        policy = version_policy_decision(config, version)
        if policy.state in frozen_states and policy.refresh != "false":
            raise TranslationMigrationError(
                f"Version {version} is {policy.state!r} but has refresh={policy.refresh!r}; "
                "published and archived versions must use refresh=false"
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
        versions = [version for version in requested_targets if version != source_version]
        for version in requested_targets:
            validate_supported_version(config, version)
        for version in versions:
            if not version_policy_allows_manual_migration(config, version):
                raise TranslationMigrationError(
                    f"Version {version!r} is not allowed as a migration target "
                    "by version_policy.migrate_into"
                )
    else:
        versions = [
            version
            for version in config.template.supported_versions
            if version_policy_decision(config, version).migrate_into == "auto"
        ]
    return [version for version in versions if version != source_version]


def version_policy_decision(
    config: TranslationRepositoryConfig,
    version: str,
) -> VersionPolicyValues:
    """Return the effective lifecycle policy for one supported version."""

    validate_supported_version(config, version)
    decision = config.version_policy.defaults
    for rule in config.version_policy.rules:
        if version_matches_range(version, rule.match):
            decision = merge_version_policy_values(decision, rule.values)
    override = config.version_policy.overrides.get(version)
    if override is not None:
        decision = merge_version_policy_values(decision, override)
    return decision


def version_policy_allows_auto_refresh(
    config: TranslationRepositoryConfig,
    version: str,
) -> bool:
    """Return whether automation may rebuild a branch from clean artifacts."""

    return version_policy_decision(config, version).refresh == "artifact"


def version_policy_allows_manual_refresh(
    config: TranslationRepositoryConfig,
    version: str,
) -> bool:
    """Return whether an operator-triggered sync may refresh a version branch."""

    return version_policy_decision(config, version).refresh in {"artifact", "manual"}


def version_policy_allows_manual_migration(
    config: TranslationRepositoryConfig,
    version: str,
) -> bool:
    """Return whether an explicitly requested migration may target a version."""

    return version_policy_decision(config, version).migrate_into in {"auto", "manual"}


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


def version_matches_range(version: str, expression: str) -> bool:
    """Return whether ``version`` satisfies a simple semver range expression."""

    version_key = version_sort_key(version)
    terms = expression.split()
    if not terms:
        raise TranslationMigrationError("Version policy match expression must not be empty")
    return all(_version_matches_range_term(version_key, term) for term in terms)


def merge_version_policy_values(
    base: VersionPolicyValues,
    overlay: VersionPolicyPatch,
) -> VersionPolicyValues:
    """Apply only fields explicitly present in a rule or exact override."""

    return VersionPolicyValues(
        state=overlay.state if overlay.state is not None else base.state,
        refresh=overlay.refresh if overlay.refresh is not None else base.refresh,
        migrate_into=(
            overlay.migrate_into if overlay.migrate_into is not None else base.migrate_into
        ),
        publish_release=(
            overlay.publish_release if overlay.publish_release is not None else base.publish_release
        ),
        reason=overlay.reason if overlay.reason is not None else base.reason,
    )


def sorted_versions(versions: Iterable[str]) -> list[str]:
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


def _load_version_policy(payload: object) -> VersionPolicyConfig:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TranslationMigrationError("translation-config.yml version_policy must be a mapping")
    _reject_unknown_keys(payload, {"defaults", "overrides", "rules"}, "version_policy")

    defaults = merge_version_policy_values(
        VersionPolicyValues(
            state="available",
            refresh="false",
            migrate_into="false",
            publish_release=False,
            reason="available scaffold only; opt in before translating",
        ),
        _load_version_policy_patch(payload.get("defaults", {})),
    )

    rules_payload = payload.get("rules", [])
    if not isinstance(rules_payload, list):
        raise TranslationMigrationError("version_policy.rules must be a list")
    rules = tuple(_load_version_policy_rule(item) for item in rules_payload)

    overrides_payload = payload.get("overrides", {})
    if not isinstance(overrides_payload, dict):
        raise TranslationMigrationError("version_policy.overrides must be a mapping")
    overrides = {
        version: _load_version_policy_patch(item)
        for version, item in overrides_payload.items()
        if _validate_policy_override_version(version)
    }

    return VersionPolicyConfig(defaults=defaults, rules=rules, overrides=overrides)


def _load_version_policy_rule(payload: object) -> VersionPolicyRule:
    if not isinstance(payload, dict):
        raise TranslationMigrationError("Each version_policy rule must be a mapping")
    _reject_unknown_keys(
        payload,
        {"match", "migrate_into", "publish_release", "reason", "refresh", "state"},
        "version_policy rule",
    )
    match = _required_str(payload, "match")
    # Validate early so bad operators fail during config load, not mid-workflow.
    version_matches_range("v0.0.0", match)
    return VersionPolicyRule(
        match=match,
        values=_load_version_policy_patch(
            {key: value for key, value in payload.items() if key != "match"}
        ),
    )


def _load_version_policy_patch(payload: object) -> VersionPolicyPatch:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TranslationMigrationError("Version policy values must be a mapping")
    _reject_unknown_keys(
        payload,
        {"migrate_into", "publish_release", "reason", "refresh", "state"},
        "version policy values",
    )
    return VersionPolicyPatch(
        state=_present_lifecycle_state(payload, "state"),
        refresh=_present_refresh_policy(payload, "refresh"),
        migrate_into=_present_migration_policy(payload, "migrate_into"),
        publish_release=_present_bool(payload, "publish_release"),
        reason=_present_str(payload, "reason"),
    )


def _present_refresh_policy(payload: dict[object, object], key: str) -> VersionRefreshPolicy | None:
    if key not in payload:
        return None
    value = payload[key]
    if value is False:
        return "false"
    if value is True:
        raise TranslationMigrationError(
            f"Expected {key!r} to use explicit value 'artifact' instead of true"
        )
    if value not in {"artifact", "manual", "false"}:
        raise TranslationMigrationError(f"Expected {key!r} to be one of artifact, manual, false")
    return value


def _present_migration_policy(
    payload: dict[object, object],
    key: str,
) -> VersionMigrationPolicy | None:
    if key not in payload:
        return None
    value = payload[key]
    if value is False:
        return "false"
    if value is True:
        raise TranslationMigrationError(
            f"Expected {key!r} to use explicit value 'auto' instead of true"
        )
    if value not in {"auto", "manual", "false"}:
        raise TranslationMigrationError(f"Expected {key!r} to be one of auto, manual, false")
    return value


def _present_bool(payload: dict[object, object], key: str) -> bool | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, bool):
        raise TranslationMigrationError(f"Expected boolean at {key!r}")
    return value


def _present_lifecycle_state(
    payload: dict[object, object],
    key: str,
) -> VersionLifecycleState | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or value not in VERSION_LIFECYCLE_STATES:
        raise TranslationMigrationError(
            f"Expected {key!r} to be one of {', '.join(VERSION_LIFECYCLE_STATES)}"
        )
    return cast(VersionLifecycleState, value)


def _present_str(payload: dict[object, object], key: str) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise TranslationMigrationError(f"Expected non-empty string at {key!r}")
    return value


def _validate_policy_override_version(version: object) -> bool:
    if not isinstance(version, str):
        raise TranslationMigrationError("version_policy override keys must be strings")
    version_sort_key(version)
    return True


def _version_matches_range_term(version_key: tuple[int, ...], term: str) -> bool:
    for operator in (">=", "<=", ">", "<", "=="):
        if term.startswith(operator):
            expected = version_sort_key(term[len(operator) :])
            return _compare_version_key(version_key, operator, expected)
    if term.endswith("+"):
        expected = version_sort_key(term[:-1])
        return version_key >= expected
    expected = version_sort_key(term)
    return version_key == expected


def _compare_version_key(
    version_key: tuple[int, ...],
    operator: str,
    expected: tuple[int, ...],
) -> bool:
    if operator == ">=":
        return version_key >= expected
    if operator == "<=":
        return version_key <= expected
    if operator == ">":
        return version_key > expected
    if operator == "<":
        return version_key < expected
    if operator == "==":
        return version_key == expected
    raise TranslationMigrationError(f"Unsupported version range operator {operator!r}")


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


def _optional_bool(payload: object, key: str, *, default: bool) -> bool:
    if not isinstance(payload, dict):
        raise TranslationMigrationError(f"Expected mapping while reading {key!r}")
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise TranslationMigrationError(f"Expected boolean at {key!r}")
    return value


def _optional_str(payload: object, key: str, *, default: str = "") -> str:
    if not isinstance(payload, dict):
        raise TranslationMigrationError(f"Expected mapping while reading {key!r}")
    value = payload.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise TranslationMigrationError(f"Expected string at {key!r}")
    return value


def _duplicate_items(items: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def _reject_unknown_keys(payload: object, allowed: set[str], section: str) -> None:
    """Reject misspelled or retired configuration fields."""

    if not isinstance(payload, dict):
        raise TranslationMigrationError(f"{section} must be a mapping")
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise TranslationMigrationError(f"Unknown {section} field(s): {', '.join(unknown)}")


DSW_PREVIEW_RUNTIMES = load_preview_runtimes()
