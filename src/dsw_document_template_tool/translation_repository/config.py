"""Strict loader for public translated-template repository configuration."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from ..yaml_config import YamlConfigError, load_yaml_file
from .errors import TranslationRepositoryError
from .models import (
    VERSION_LIFECYCLE_STATES,
    BranchConfig,
    MigrationConfig,
    PublicReadmeConfig,
    TemplateConfig,
    ToolingConfig,
    TranslationConfig,
    TranslationRepositoryConfig,
    VersionLifecycleState,
    VersionMigrationPolicy,
    VersionPolicyConfig,
    VersionPolicyPatch,
    VersionPolicyRule,
    VersionPolicyValues,
    VersionRefreshPolicy,
    XliffExchangeConfig,
)
from .policy import merge_version_policy_values, version_policy_decision
from .validation import (
    optional_bool,
    optional_str,
    reject_unknown_keys,
    required_str,
    required_str_list,
)
from .versions import version_matches_range, version_sort_key

TRANSLATION_CONFIG_SCHEMA_VERSION = 2


def load_translation_repository_config(path: Path) -> TranslationRepositoryConfig:
    """Load and validate ``translation-config.yml``."""

    try:
        payload = load_yaml_file(path)
    except (OSError, YamlConfigError) as exc:
        raise TranslationRepositoryError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise TranslationRepositoryError("translation-config.yml must contain a mapping")
    reject_unknown_keys(
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
        raise TranslationRepositoryError(
            f"translation-config.yml schema_version must be {TRANSLATION_CONFIG_SCHEMA_VERSION}"
        )

    template = _load_template_config(_required_section(payload, "template"))
    translation = _load_translation_config(_required_section(payload, "translation"))
    config = TranslationRepositoryConfig(
        template=template,
        translation=translation,
        branches=_load_branch_config(_required_section(payload, "branches")),
        migration=_load_migration_config(_required_section(payload, "migration")),
        public_readme=_load_public_readme_config(payload.get("public_readme")),
        tooling=_load_tooling_config(_required_section(payload, "tooling")),
        version_policy=_load_version_policy(payload.get("version_policy")),
        xliff_exchange=_load_xliff_exchange_config(
            payload.get("xliff_exchange"),
            template=template,
            translation=translation,
        ),
    )
    _validate_repository_config(config)
    return config


def _required_section(payload: dict[object, object], key: str) -> dict[object, object]:
    try:
        section = payload[key]
    except KeyError as exc:
        raise TranslationRepositoryError(
            f"translation-config.yml is missing top-level key {key!r}"
        ) from exc
    if not isinstance(section, dict):
        raise TranslationRepositoryError(f"translation-config.yml {key} must be a mapping")
    return section


def _load_template_config(payload: object) -> TemplateConfig:
    reject_unknown_keys(
        payload,
        {
            "organization_id",
            "supported_ref_spec",
            "supported_versions",
            "template_id",
            "upstream_repository",
        },
        "template",
    )
    return TemplateConfig(
        organization_id=required_str(payload, "organization_id"),
        template_id=required_str(payload, "template_id"),
        upstream_repository=required_str(payload, "upstream_repository"),
        supported_ref_spec=cast(str, optional_str(payload, "supported_ref_spec")),
        supported_versions=tuple(required_str_list(payload, "supported_versions")),
    )


def _load_translation_config(payload: object) -> TranslationConfig:
    reject_unknown_keys(
        payload,
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
    return TranslationConfig(
        source_language=required_str(payload, "source_language"),
        target_language=required_str(payload, "target_language"),
        target_language_label=required_str(payload, "target_language_label"),
        translated_template_organization_id=required_str(
            payload,
            "translated_template_organization_id",
        ),
        translated_template_description=optional_str(
            payload,
            "translated_template_description",
            default=None,
        ),
        translated_template_id=required_str(payload, "translated_template_id"),
        translated_template_name=required_str(payload, "translated_template_name"),
    )


def _load_branch_config(payload: object) -> BranchConfig:
    reject_unknown_keys(payload, {"control_branch", "version_branch_prefix"}, "branches")
    return BranchConfig(
        control_branch=cast(str, optional_str(payload, "control_branch", default="master")),
        version_branch_prefix=required_str(payload, "version_branch_prefix"),
    )


def _load_tooling_config(payload: object) -> ToolingConfig:
    reject_unknown_keys(payload, {"ref", "repository"}, "tooling")
    return ToolingConfig(
        repository=required_str(payload, "repository"),
        ref=required_str(payload, "ref"),
    )


def _load_migration_config(payload: object) -> MigrationConfig:
    reject_unknown_keys(
        payload,
        {
            "auto_merge_when_clean",
            "auto_pr_branch_prefix",
            "auto_pr_enabled",
            "mode",
            "non_exact_policy",
        },
        "migration",
    )
    return MigrationConfig(
        mode=required_str(payload, "mode"),
        non_exact_policy=required_str(payload, "non_exact_policy"),
        auto_pr_enabled=optional_bool(payload, "auto_pr_enabled", default=False),
        auto_pr_branch_prefix=cast(
            str,
            optional_str(payload, "auto_pr_branch_prefix", default="automation/migrate"),
        ),
        auto_merge_when_clean=optional_bool(
            payload,
            "auto_merge_when_clean",
            default=False,
        ),
    )


def _load_xliff_exchange_config(
    payload: object,
    *,
    template: TemplateConfig,
    translation: TranslationConfig,
) -> XliffExchangeConfig:
    section = {} if payload is None else payload
    if not isinstance(section, dict):
        raise TranslationRepositoryError("translation-config.yml xliff_exchange must be a mapping")
    reject_unknown_keys(section, {"enabled", "path"}, "xliff_exchange")
    source_template_id = f"{template.organization_id}-{template.template_id}"
    return XliffExchangeConfig(
        enabled=optional_bool(section, "enabled", default=False),
        path=Path(
            cast(
                str,
                optional_str(
                    section,
                    "path",
                    default=f"xliff/{source_template_id}.{translation.target_language}.xlf",
                ),
            )
        ),
    )


def _load_public_readme_config(payload: object) -> PublicReadmeConfig:
    section = {} if payload is None else payload
    if not isinstance(section, dict):
        raise TranslationRepositoryError("translation-config.yml public_readme must be a mapping")
    reject_unknown_keys(section, {"path"}, "public_readme")
    return PublicReadmeConfig(
        path=Path(
            cast(
                str,
                optional_str(
                    section,
                    "path",
                    default="workspace/document-templates/public-readme/README.md",
                ),
            )
        )
    )


def _validate_repository_config(config: TranslationRepositoryConfig) -> None:
    template = config.template
    if not template.supported_versions:
        raise TranslationRepositoryError("template.supported_versions must not be empty")
    duplicates = _duplicate_items(template.supported_versions)
    if duplicates:
        raise TranslationRepositoryError(
            "template.supported_versions contains duplicate entries: " + ", ".join(duplicates)
        )
    for version in template.supported_versions:
        version_sort_key(version)
    if config.migration.mode != "exact-only":
        raise TranslationRepositoryError(
            "Only exact-only cross-version synchronization is currently supported"
        )
    if config.migration.non_exact_policy != "leave_empty_needs_translation":
        raise TranslationRepositoryError(
            "Only leave_empty_needs_translation non-exact migration policy is currently supported"
        )
    if not config.migration.auto_pr_branch_prefix:
        raise TranslationRepositoryError("migration.auto_pr_branch_prefix must not be empty")
    if not config.branches.control_branch:
        raise TranslationRepositoryError("branches.control_branch must not be empty")
    if not config.branches.version_branch_prefix:
        raise TranslationRepositoryError("branches.version_branch_prefix must not be empty")
    _validate_relative_path(config.public_readme.path, "public_readme.path")
    _validate_relative_path(config.xliff_exchange.path, "xliff_exchange.path")
    _validate_version_lifecycle_policy(config)


def _validate_relative_path(path: Path, name: str) -> None:
    if path.is_absolute() or ".." in path.parts:
        raise TranslationRepositoryError(f"{name} must be a repo-relative path")


def _validate_version_lifecycle_policy(config: TranslationRepositoryConfig) -> None:
    frozen_states = {"published", "archived"}
    for version in config.template.supported_versions:
        policy = version_policy_decision(config, version)
        if policy.state not in frozen_states:
            continue
        mutable_fields = []
        if policy.refresh != "false":
            mutable_fields.append(f"refresh={policy.refresh!r}")
        if policy.migrate_into != "false":
            mutable_fields.append(f"migrate_into={policy.migrate_into!r}")
        if mutable_fields:
            raise TranslationRepositoryError(
                f"Version {version} is {policy.state!r} but has "
                f"{', '.join(mutable_fields)}; published and archived versions must "
                "use refresh=false and migrate_into=false"
            )


def _load_version_policy(payload: object) -> VersionPolicyConfig:
    section = {} if payload is None else payload
    if not isinstance(section, dict):
        raise TranslationRepositoryError("translation-config.yml version_policy must be a mapping")
    reject_unknown_keys(section, {"defaults", "overrides", "rules"}, "version_policy")
    defaults = merge_version_policy_values(
        VersionPolicyValues(
            state="available",
            refresh="false",
            migrate_into="false",
            publish_release=False,
            reason="available scaffold only; opt in before translating",
        ),
        _load_version_policy_patch(section.get("defaults")),
    )
    rules_payload = section.get("rules", [])
    if not isinstance(rules_payload, list):
        raise TranslationRepositoryError("version_policy.rules must be a list")
    overrides_payload = section.get("overrides", {})
    if not isinstance(overrides_payload, dict):
        raise TranslationRepositoryError("version_policy.overrides must be a mapping")
    overrides = {
        version: _load_version_policy_patch(item)
        for version, item in overrides_payload.items()
        if _validate_policy_override_version(version)
    }
    return VersionPolicyConfig(
        defaults=defaults,
        rules=tuple(_load_version_policy_rule(item) for item in rules_payload),
        overrides=overrides,
    )


def _load_version_policy_rule(payload: object) -> VersionPolicyRule:
    if not isinstance(payload, dict):
        raise TranslationRepositoryError("Each version_policy rule must be a mapping")
    reject_unknown_keys(
        payload,
        {"match", "migrate_into", "publish_release", "reason", "refresh", "state"},
        "version_policy rule",
    )
    match = required_str(payload, "match")
    version_matches_range("v0.0.0", match)
    return VersionPolicyRule(
        match=match,
        values=_load_version_policy_patch(
            {key: value for key, value in payload.items() if key != "match"}
        ),
    )


def _load_version_policy_patch(payload: object) -> VersionPolicyPatch:
    section = {} if payload is None else payload
    if not isinstance(section, dict):
        raise TranslationRepositoryError("Version policy values must be a mapping")
    reject_unknown_keys(
        section,
        {"migrate_into", "publish_release", "reason", "refresh", "state"},
        "version policy values",
    )
    return VersionPolicyPatch(
        state=_present_lifecycle_state(section, "state"),
        refresh=_present_refresh_policy(section, "refresh"),
        migrate_into=_present_migration_policy(section, "migrate_into"),
        publish_release=_present_bool(section, "publish_release"),
        reason=_present_str(section, "reason"),
    )


def _present_refresh_policy(
    payload: dict[object, object],
    key: str,
) -> VersionRefreshPolicy | None:
    if key not in payload:
        return None
    value = payload[key]
    if value is False:
        return "false"
    if value is True:
        raise TranslationRepositoryError(
            f"Expected {key!r} to use explicit value 'artifact' instead of true"
        )
    if value not in {"artifact", "manual", "false"}:
        raise TranslationRepositoryError(f"Expected {key!r} to be one of artifact, manual, false")
    return cast(VersionRefreshPolicy, value)


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
        raise TranslationRepositoryError(
            f"Expected {key!r} to use explicit value 'auto' instead of true"
        )
    if value not in {"auto", "manual", "false"}:
        raise TranslationRepositoryError(f"Expected {key!r} to be one of auto, manual, false")
    return cast(VersionMigrationPolicy, value)


def _present_bool(payload: dict[object, object], key: str) -> bool | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, bool):
        raise TranslationRepositoryError(f"Expected boolean at {key!r}")
    return value


def _present_lifecycle_state(
    payload: dict[object, object],
    key: str,
) -> VersionLifecycleState | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or value not in VERSION_LIFECYCLE_STATES:
        raise TranslationRepositoryError(
            f"Expected {key!r} to be one of {', '.join(VERSION_LIFECYCLE_STATES)}"
        )
    return cast(VersionLifecycleState, value)


def _present_str(payload: dict[object, object], key: str) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise TranslationRepositoryError(f"Expected non-empty string at {key!r}")
    return value


def _validate_policy_override_version(version: object) -> bool:
    if not isinstance(version, str):
        raise TranslationRepositoryError("version_policy override keys must be strings")
    version_sort_key(version)
    return True


def _duplicate_items(items: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates
