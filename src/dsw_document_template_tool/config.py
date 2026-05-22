"""Workflow config loading and validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .models import (
    ApiConfig,
    FixtureConfig,
    ProjectSeedConfig,
    RegressionConfig,
    SubjectConfig,
    TdkConfig,
    WorkflowConfig,
)

DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_POLL_SECONDS = 1.0
DEFAULT_WORKFLOW_CONFIG_PATH = Path("config/regression.preview.yml")
UNEXPANDED_ENV_PATTERN = "${"


class WorkflowConfigError(ValueError):
    """Raised when the YAML config is missing required workflow fields."""


def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def _require_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise WorkflowConfigError(f"Expected mapping at `{key}`")
    return value


def _require_str(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WorkflowConfigError(f"Expected non-empty string at `{key}`")
    return _reject_unexpanded_env_var(value.strip(), key)


def _optional_str(parent: dict[str, Any], key: str) -> str | None:
    value = parent.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WorkflowConfigError(f"Expected string at `{key}`")
    return _reject_unexpanded_env_var(value.strip(), key)


def _optional_bool(parent: dict[str, Any], key: str, default: bool) -> bool:
    value = parent.get(key, default)
    if not isinstance(value, bool):
        raise WorkflowConfigError(f"Expected boolean at `{key}`")
    return value


def _optional_float(parent: dict[str, Any], key: str, default: float) -> float:
    value = parent.get(key, default)
    if not isinstance(value, (int, float)):
        raise WorkflowConfigError(f"Expected number at `{key}`")
    return float(value)


def _optional_int(parent: dict[str, Any], key: str, default: int) -> int:
    value = parent.get(key, default)
    if not isinstance(value, int):
        raise WorkflowConfigError(f"Expected integer at `{key}`")
    return value


def _optional_str_list(parent: dict[str, Any], key: str) -> list[str]:
    value = parent.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkflowConfigError(f"Expected string list at `{key}`")
    return [item.strip() for item in value]


def _resolve_path(base_dir: Path, raw_path: str | None) -> Path | None:
    if raw_path is None:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _resolve_subject_value(base_dir: Path, kind: str, value: str) -> str:
    if kind != "local_dir":
        return value
    resolved = _resolve_path(base_dir, value)
    assert resolved is not None
    return str(resolved)


def _resolve_package_reference(base_dir: Path, value: str) -> str:
    if value.count(":") == 2:
        return value
    resolved = _resolve_path(base_dir, value)
    if resolved is not None and resolved.is_file():
        return str(resolved)
    return value


def _resolve_executable_reference(base_dir: Path, value: str | None) -> str:
    if value is None or "/" not in value:
        return value or "dsw-tdk"
    resolved = _resolve_path(base_dir, value)
    assert resolved is not None
    return str(resolved)


def _reject_unexpanded_env_var(value: str, key: str) -> str:
    if UNEXPANDED_ENV_PATTERN in value:
        raise WorkflowConfigError(
            f"Environment variable placeholder at `{key}` was not expanded: {value!r}"
        )
    return value


def load_workflow_config(config_path: str | Path) -> WorkflowConfig:
    """Load one YAML workflow config from disk."""

    path = Path(config_path).resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise WorkflowConfigError("Workflow config root must be a mapping")
    payload = _expand_env_vars(payload)
    base_dir = path.parent

    api_section = _require_dict(payload, "api")
    api = ApiConfig(
        url=_require_str(api_section, "url"),
        token=_optional_str(api_section, "token"),
        email=_optional_str(api_section, "email"),
        password=_optional_str(api_section, "password"),
        verify_ssl=_optional_bool(api_section, "verify_ssl", False),
    )
    if api.token is None and (api.email is None or api.password is None):
        raise WorkflowConfigError(
            "Provide either `api.token` or both `api.email` and `api.password`"
        )

    tdk_section = payload.get("tdk", {})
    if tdk_section is None:
        tdk_section = {}
    if not isinstance(tdk_section, dict):
        raise WorkflowConfigError("Expected mapping at `tdk`")
    tdk = TdkConfig(
        executable=_resolve_executable_reference(
            base_dir, _optional_str(tdk_section, "executable")
        ),
    )

    subjects_section = _require_dict(payload, "subjects")
    baseline_section = _require_dict(subjects_section, "baseline")
    candidate_section = _require_dict(subjects_section, "candidate")

    baseline = SubjectConfig(
        kind=_require_str(baseline_section, "kind"),
        value=_resolve_subject_value(
            base_dir,
            _require_str(baseline_section, "kind"),
            _require_str(baseline_section, "value"),
        ),
        verify=_optional_bool(baseline_section, "verify", True),
        stage_id=_optional_str(baseline_section, "stage_id"),
    )
    candidate = SubjectConfig(
        kind=_require_str(candidate_section, "kind"),
        value=_resolve_subject_value(
            base_dir,
            _require_str(candidate_section, "kind"),
            _require_str(candidate_section, "value"),
        ),
        verify=_optional_bool(candidate_section, "verify", True),
        stage_id=_optional_str(candidate_section, "stage_id"),
    )

    regression_section = _require_dict(payload, "regression")
    regression = RegressionConfig(
        mode=_require_str(regression_section, "mode"),
        format_uuid=_require_str(regression_section, "format_uuid"),
        output_dir=_resolve_path(base_dir, _require_str(regression_section, "output_dir"))
        or base_dir,
        timeout_seconds=_optional_int(
            regression_section, "timeout_seconds", DEFAULT_TIMEOUT_SECONDS
        ),
        poll_seconds=_optional_float(regression_section, "poll_seconds", DEFAULT_POLL_SECONDS),
        cleanup_projects=_optional_bool(regression_section, "cleanup_projects", False),
        ignore_patterns=_optional_str_list(regression_section, "ignore_patterns"),
    )

    fixtures_payload = payload.get("fixtures")
    if not isinstance(fixtures_payload, list) or not fixtures_payload:
        raise WorkflowConfigError("Expected non-empty list at `fixtures`")
    fixtures: list[FixtureConfig] = []
    for index, fixture_payload in enumerate(fixtures_payload, start=1):
        if not isinstance(fixture_payload, dict):
            raise WorkflowConfigError(f"Fixture #{index} must be a mapping")
        project_payload = fixture_payload.get("project")
        project = None
        if project_payload is not None:
            if not isinstance(project_payload, dict):
                raise WorkflowConfigError(f"Fixture #{index} `project` must be a mapping")
            project = ProjectSeedConfig(
                name=_require_str(project_payload, "name"),
                knowledge_model_package_id=_resolve_package_reference(
                    base_dir,
                    _require_str(project_payload, "knowledge_model_package_id"),
                ),
                question_tag_uuids=_optional_str_list(project_payload, "question_tag_uuids"),
                visibility=_optional_str(project_payload, "visibility")
                or "PrivateProjectVisibility",
                sharing=_optional_str(project_payload, "sharing") or "RestrictedProjectSharing",
            )
        fixture = FixtureConfig(
            name=_require_str(fixture_payload, "name"),
            project_uuid=_optional_str(fixture_payload, "project_uuid"),
            project_event_uuid=_optional_str(fixture_payload, "project_event_uuid"),
            project=project,
            events_file=_resolve_path(base_dir, _optional_str(fixture_payload, "events_file")),
        )
        if fixture.project_uuid is None and fixture.project is None:
            raise WorkflowConfigError(
                f"Fixture `{fixture.name}` must define either `project_uuid` or `project`"
            )
        if fixture.events_file is not None and not fixture.events_file.is_file():
            raise WorkflowConfigError(
                f"Fixture `{fixture.name}` references missing events_file {fixture.events_file}"
            )
        fixtures.append(fixture)

    if regression.mode == "document":
        for fixture in fixtures:
            if fixture.project_event_uuid is None and fixture.events_file is None:
                raise WorkflowConfigError(
                    "Document mode fixtures must define `project_event_uuid` or `events_file` "
                    f"for `{fixture.name}`"
                )

    return WorkflowConfig(
        config_path=path,
        api=api,
        tdk=tdk,
        baseline=baseline,
        candidate=candidate,
        regression=regression,
        fixtures=fixtures,
    )
