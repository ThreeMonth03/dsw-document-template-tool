"""Dataclasses shared by the workflow, API client, and CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PRIVATE_PROJECT_VISIBILITY = "PrivateProjectVisibility"
RESTRICTED_PROJECT_SHARING = "RestrictedProjectSharing"


@dataclass(frozen=True)
class TemplateCoordinates:
    """Stable document template coordinates."""

    organization_id: str
    template_id: str
    version: str

    @property
    def full_id(self) -> str:
        """Return ``organizationId:templateId:version``."""

        return f"{self.organization_id}:{self.template_id}:{self.version}"


@dataclass(frozen=True)
class DocumentTemplateReference:
    """Released template identifiers exposed by different DSW API generations."""

    template_id: str | None = None
    uuid: str | None = None


@dataclass(frozen=True)
class ApiConfig:
    """DSW API connection configuration."""

    url: str
    token: str | None = None
    email: str | None = None
    password: str | None = None
    verify_ssl: bool = False


@dataclass(frozen=True)
class TdkConfig:
    """Configuration for the `dsw-tdk` executable."""

    executable: str = "dsw-tdk"


@dataclass(frozen=True)
class SubjectConfig:
    """One regression subject, such as baseline or candidate."""

    kind: str
    value: str
    verify: bool = True
    stage_id: str | None = None


@dataclass(frozen=True)
class ProjectSeedConfig:
    """Recipe for creating a fixture project from a knowledge model package."""

    name: str
    knowledge_model_package_id: str
    question_tag_uuids: list[str] = field(default_factory=list)
    visibility: str = PRIVATE_PROJECT_VISIBILITY
    sharing: str = RESTRICTED_PROJECT_SHARING


@dataclass(frozen=True)
class GeneratedFixtureConfig:
    """Recipe for deterministic random fixture projects."""

    name_prefix: str
    count: int
    seed: int
    project: ProjectSeedConfig
    selection_pool_size: int
    max_events: int = 260
    max_items_per_list: int = 2
    answer_probability: float = 1.0
    require_complete_coverage: bool = False


@dataclass(frozen=True)
class FixtureConfig:
    """One regression fixture project."""

    name: str
    project_uuid: str | None = None
    project_event_uuid: str | None = None
    project: ProjectSeedConfig | None = None
    events_file: Path | None = None


@dataclass(frozen=True)
class RegressionConfig:
    """Regression execution settings."""

    assertion: str
    mode: str
    format_uuid: str
    output_dir: Path
    timeout_seconds: int
    poll_seconds: float
    cleanup_projects: bool = False
    ignore_patterns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowConfig:
    """Top-level workflow configuration loaded from YAML."""

    config_path: Path
    api: ApiConfig
    tdk: TdkConfig
    baseline: SubjectConfig | None
    candidate: SubjectConfig
    regression: RegressionConfig
    fixtures: list[FixtureConfig]
    generated_fixtures: list[GeneratedFixtureConfig] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedSubject:
    """A subject after local staging or remote lookup has completed."""

    label: str
    mode: str
    source_value: str
    display_id: str
    template_reference: DocumentTemplateReference | None = None
    draft_uuid: str | None = None
    local_dir: Path | None = None
    staged_dir: Path | None = None


@dataclass(frozen=True)
class FixtureProject:
    """Resolved fixture project information used during one regression run."""

    name: str
    project_uuid: str
    project_event_uuid: str | None
    created_by_tool: bool


@dataclass(frozen=True)
class RenderArtifact:
    """Paths for one rendered subject output."""

    raw_path: Path
    normalized_path: Path
    subject_label: str
    template_reference: str


@dataclass(frozen=True)
class FixtureRegressionResult:
    """Result for one fixture assertion."""

    fixture_name: str
    project_uuid: str
    passed: bool
    baseline: RenderArtifact | None
    candidate: RenderArtifact
    diff_path: Path | None


@dataclass(frozen=True)
class RegressionReport:
    """Final workflow report written to disk and printed by the CLI."""

    assertion: str
    mode: str
    output_dir: Path
    passed: bool
    fixture_results: list[FixtureRegressionResult]
    report_path: Path
