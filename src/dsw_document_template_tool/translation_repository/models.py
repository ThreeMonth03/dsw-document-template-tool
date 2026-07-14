"""Typed configuration and path models for translated-template repositories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


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
