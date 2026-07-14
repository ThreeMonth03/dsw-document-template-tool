"""Version lifecycle and cross-version synchronization policy."""

from __future__ import annotations

from .errors import TranslationRepositoryError
from .models import TranslationRepositoryConfig, VersionPolicyPatch, VersionPolicyValues
from .versions import version_matches_range


def target_versions(
    config: TranslationRepositoryConfig,
    source_version: str,
    requested_targets: list[str] | None = None,
) -> list[str]:
    """Return supported synchronization targets for one source version."""

    validate_supported_version(config, source_version)
    if requested_targets:
        versions = [version for version in requested_targets if version != source_version]
        for version in requested_targets:
            validate_supported_version(config, version)
        for version in versions:
            if not version_policy_allows_manual_migration(config, version):
                raise TranslationRepositoryError(
                    f"Version {version!r} is not allowed as a synchronization target "
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
    """Return whether an explicitly requested sync may use a version."""

    return version_policy_decision(config, version).migrate_into in {"auto", "manual"}


def version_policy_allows_auto_migration(
    config: TranslationRepositoryConfig,
    version: str,
) -> bool:
    """Return whether automatic cross-version sync may use a version."""

    return version_policy_decision(config, version).migrate_into == "auto"


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


def validate_supported_version(config: TranslationRepositoryConfig, version: str) -> None:
    """Raise if a version is not configured as supported."""

    if version not in config.template.supported_versions:
        supported = ", ".join(config.template.supported_versions)
        raise TranslationRepositoryError(
            f"Unsupported version {version!r}. Supported versions: {supported}"
        )
