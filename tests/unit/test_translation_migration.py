"""Tests for cross-version translation migration helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsw_document_template_tool.translation_repository import (
    TranslationRepositoryError,
    clean_artifact_version_paths,
    clean_artifact_versions,
    load_preview_runtimes,
    load_translation_repository_config,
    migration_branch,
    preview_runtime_for_template,
    preview_runtime_for_version,
    preview_runtime_matrix,
    sorted_versions,
    target_versions,
    version_branch,
    version_matches_range,
    version_paths,
    version_policy_allows_auto_migration,
    version_policy_allows_auto_refresh,
    version_policy_allows_manual_migration,
    version_policy_allows_manual_refresh,
    version_policy_decision,
    version_to_number,
)


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "translation-config.yml"
    config_path.write_text(
        """
schema_version: 2

template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: https://github.com/ds-wizard/science-europe-template.git
  supported_ref_spec: v1.29.1+
  supported_versions:
    - v1.30.0
    - v1.30.1

version_policy:
  defaults:
    state: active
    refresh: artifact
    migrate_into: auto
    publish_release: true

translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant
  translated_template_organization_id: dsw
  translated_template_description: Science Europe DMP Template 的繁體中文化版本
  translated_template_id: science-europe-zh-hant
  translated_template_name: Science Europe DMP Template (zh-Hant)

branches:
  version_branch_prefix: sync/

tooling:
  repository: ThreeMonth03/dsw-document-template-tool
  ref: master

migration:
  mode: exact-only
  non_exact_policy: leave_empty_needs_translation
  auto_pr_enabled: true
  auto_pr_branch_prefix: automation/migrate
  auto_merge_when_clean: false

""".lstrip(),
        encoding="utf-8",
    )
    return config_path


def _replace_version_policy(config_text: str, policy_text: str) -> str:
    """Replace the complete policy section without creating duplicate YAML keys."""

    start = config_text.index("version_policy:\n")
    end = config_text.index("\ntranslation:\n", start)
    return f"{config_text[:start]}{policy_text.strip()}\n{config_text[end + 1 :]}"


def test_load_translation_repository_config_and_paths(tmp_path: Path) -> None:
    """The migration config should derive stable version-specific paths."""

    config = load_translation_repository_config(_write_config(tmp_path))
    paths = version_paths(config, "v1.30.1")

    assert config.template.supported_ref_spec == "v1.29.1+"
    assert config.template.supported_versions == ("v1.30.0", "v1.30.1")
    assert version_branch(config, "v1.30.1") == "sync/v1.30.1"
    assert migration_branch(config, "v1.30.0", "v1.30.1") == (
        "automation/migrate-v1.30.0-to-v1.30.1"
    )
    assert (
        config.translation.translated_template_description
        == "Science Europe DMP Template 的繁體中文化版本"
    )
    assert config.branches.control_branch == "master"
    assert config.xliff_exchange.enabled is False
    assert config.xliff_exchange.path == Path("xliff/dsw-science-europe.zh_Hant.xlf")
    assert config.public_readme.path == Path("workspace/document-templates/public-readme/README.md")
    assert paths.version_number == "1.30.1"
    assert paths.workspace_template_name == "dsw-science-europe-1.30.1"
    assert paths.compact_template_dir.as_posix() == (
        "workspace/document-templates/compact/dsw-science-europe-1.30.1"
    )
    assert paths.translation_tree_dir.as_posix() == (
        "workspace/document-templates/translation/dsw-science-europe-1.30.1"
    )
    assert paths.translated_template_package.as_posix() == (
        "outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/"
        "dsw-science-europe-zh-hant-1.30.1.zip"
    )


def test_translation_config_rejects_duplicate_keys(tmp_path: Path) -> None:
    """A duplicate operations setting must not silently select one value."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "  ref: master",
            "  ref: master\n  ref: unreviewed",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="duplicate key 'ref'"):
        load_translation_repository_config(config_path)


def test_preview_runtime_config_rejects_duplicate_keys(tmp_path: Path) -> None:
    """A duplicate runtime field must fail before matrix generation."""

    config_path = tmp_path / "dsw-compat.yml"
    config_path.write_text(
        """
schema_version: 1
runtimes:
  - metamodel_key: 18-0
    metamodel_version: "18.0"
    dsw_version: "4.30"
    dsw_version: "4.31"
    tdk_version: "4.30.1"
    min_version: v1.30.0
    max_version: null
    upstream_template_artifact_refs: v1.30.0+
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="duplicate key 'dsw_version'"):
        load_preview_runtimes(config_path)


def test_load_translation_repository_config_accepts_custom_public_readme_path(
    tmp_path: Path,
) -> None:
    """Downstream repos may choose where the user-facing README lives."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """
public_readme:
  path: docs/template-readme/README.md
""",
        encoding="utf-8",
    )

    config = load_translation_repository_config(config_path)

    assert config.public_readme.path == Path("docs/template-readme/README.md")


def test_load_translation_repository_config_rejects_unsafe_public_readme_path(
    tmp_path: Path,
) -> None:
    """The public README path should stay inside the public repository."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """
public_readme:
  path: ../README.md
""",
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="public_readme.path"):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_duplicate_supported_versions(
    tmp_path: Path,
) -> None:
    """Supported template versions should be unambiguous."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "    - v1.30.1",
            "    - v1.30.1\n    - v1.30.1",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="duplicate"):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_invalid_supported_versions(tmp_path: Path) -> None:
    """Supported versions should use explicit upstream tag names."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("    - v1.30.1", "    - 1.30.1"),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="Expected a version tag"):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_unknown_non_exact_policy(tmp_path: Path) -> None:
    """Migration policy names should be allowlisted, not silently accepted."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "non_exact_policy: leave_empty_needs_translation",
            "non_exact_policy: copy_if_similar",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="non-exact migration policy"):
        load_translation_repository_config(config_path)


def test_translation_config_without_version_policy_is_scaffold_only(
    tmp_path: Path,
) -> None:
    """Missing policy should not accidentally opt every upstream tag into translation."""

    config_path = _write_config(tmp_path)
    payload = config_path.read_text(encoding="utf-8")
    start = payload.index("version_policy:\n")
    end = payload.index("translation:\n")
    config_path.write_text(payload[:start] + payload[end:], encoding="utf-8")

    config = load_translation_repository_config(config_path)

    assert version_policy_decision(config, "v1.30.1").state == "available"
    assert version_policy_allows_auto_refresh(config, "v1.30.1") is False
    assert version_policy_allows_manual_refresh(config, "v1.30.1") is False
    assert version_policy_decision(config, "v1.30.1").migrate_into == "false"
    assert version_policy_decision(config, "v1.30.1").publish_release is False
    assert version_policy_allows_auto_migration(config, "v1.30.1") is False
    assert version_policy_allows_manual_migration(config, "v1.30.1") is False
    assert target_versions(config, "v1.30.0") == []


@pytest.mark.parametrize("state", ["published", "archived"])
def test_frozen_versions_reject_automatic_migration(
    tmp_path: Path,
    state: str,
) -> None:
    """Frozen branches must not remain cross-version synchronization targets."""

    config_path = _write_config(tmp_path)
    config_text = config_path.read_text(encoding="utf-8")
    policy = f"""
version_policy:
  defaults:
    state: active
    refresh: artifact
    migrate_into: auto
    publish_release: true
  overrides:
    v1.30.0:
      state: {state}
      refresh: false
      migrate_into: auto
"""
    config_path.write_text(
        _replace_version_policy(config_text, policy),
        encoding="utf-8",
    )

    with pytest.raises(
        TranslationRepositoryError,
        match="refresh=false and migrate_into=false",
    ):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_string_booleans(tmp_path: Path) -> None:
    """Quoted booleans should fail instead of being coerced by Python truthiness."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "auto_merge_when_clean: false",
            'auto_merge_when_clean: "false"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="Expected boolean"):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_auto_pr_string_booleans(tmp_path: Path) -> None:
    """Migration automation flags should also reject quoted booleans."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "auto_pr_enabled: true",
            'auto_pr_enabled: "true"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="Expected boolean"):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_empty_bot_branch_prefix(tmp_path: Path) -> None:
    """Migration bot branches need a stable non-empty namespace."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "auto_pr_branch_prefix: automation/migrate",
            "auto_pr_branch_prefix: ''",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="auto_pr_branch_prefix"):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_retired_or_misspelled_fields(
    tmp_path: Path,
) -> None:
    """Unknown fields should fail instead of becoming inert configuration."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\npublish:\n  enabled: false\n",
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="Unknown translation-config.yml"):
        load_translation_repository_config(config_path)


def test_translation_config_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    """Schema changes should be explicit instead of silently accepted."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "schema_version: 2",
            "schema_version: 1",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="schema_version must be 2"):
        load_translation_repository_config(config_path)


def test_preview_runtime_config_rejects_string_booleans(tmp_path: Path) -> None:
    """DSW runtime flags should fail loudly when YAML values are quoted."""

    compat_path = tmp_path / "dsw-compat.yml"
    compat_path.write_text(
        """
schema_version: 1
runtimes:
  - metamodel_key: "18-0"
    metamodel_version: "18.0"
    dsw_version: "4.30"
    tdk_version: "4.30.2"
    min_version: "v1.30.0"
    max_version: null
    upstream_template_artifact_refs: "v1.30.0+"
    run_preview_regression: "false"
    strict_project_preview: true
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="Expected boolean"):
        load_preview_runtimes(compat_path)


def test_preview_runtime_config_rejects_unknown_fields(tmp_path: Path) -> None:
    """Misspelled runtime fields should not silently select default behavior."""

    compat_path = tmp_path / "dsw-compat.yml"
    compat_path.write_text(
        """
schema_version: 1
runtimes:
  - metamodel_key: "18-0"
    metamodel_version: "18.0"
    dsw_version: "4.30"
    tdk_version: "4.30.2"
    min_version: "v1.30.0"
    max_version: null
    upstream_template_artifact_refs: "v1.30.0+"
    run_preview_regresion: true
    strict_project_preview: true
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="run_preview_regresion"):
        load_preview_runtimes(compat_path)


def test_preview_runtime_config_rejects_unsupported_schema(tmp_path: Path) -> None:
    """Compatibility config schema changes should require an explicit loader update."""

    compat_path = tmp_path / "dsw-compat.yml"
    compat_path.write_text("schema_version: 2\nruntimes: []\n", encoding="utf-8")

    with pytest.raises(TranslationRepositoryError, match="schema_version must be 1"):
        load_preview_runtimes(compat_path)


def test_clean_artifact_version_paths_follow_ci_artifact_layout(tmp_path: Path) -> None:
    """Downloaded clean artifacts should expose generated workspace inputs by version."""

    config = load_translation_repository_config(_write_config(tmp_path))
    paths = clean_artifact_version_paths(config, "v1.30.1", tmp_path / "artifact")

    assert paths.compact_template_dir.as_posix().endswith(
        "artifact/upstream-workspaces/dsw-science-europe/v1.30.1/compact/dsw-science-europe-1.30.1"
    )
    assert paths.expanded_template_dir.as_posix().endswith(
        "artifact/upstream-workspaces/dsw-science-europe/v1.30.1/expanded/dsw-science-europe-1.30.1"
    )
    assert paths.translation_tree_dir.as_posix().endswith(
        "artifact/upstream-workspaces/dsw-science-europe/v1.30.1/"
        "translation/dsw-science-europe-1.30.1"
    )


def test_clean_artifact_versions_are_semver_sorted(tmp_path: Path) -> None:
    """Clean artifact discovery should not use lexicographic version ordering."""

    config = load_translation_repository_config(_write_config(tmp_path))
    workspace_root = tmp_path / "artifact" / "upstream-workspaces" / "dsw-science-europe"
    for version in ("v1.30.10", "v1.30.2", "v1.30.1", "not-a-version"):
        (workspace_root / version).mkdir(parents=True)

    assert clean_artifact_versions(config=config, artifact_root=tmp_path / "artifact") == [
        "v1.30.1",
        "v1.30.2",
        "v1.30.10",
    ]


def test_target_versions_excludes_source_and_validates_targets(tmp_path: Path) -> None:
    """Migration targets should be explicit supported versions, excluding the source."""

    config = load_translation_repository_config(_write_config(tmp_path))

    assert target_versions(config, "v1.30.0") == ["v1.30.1"]
    assert target_versions(config, "v1.30.0", ["v1.30.0", "v1.30.1"]) == ["v1.30.1"]
    with pytest.raises(TranslationRepositoryError):
        target_versions(config, "v1.30.0", ["v9.99.9"])


def test_version_policy_rules_and_overrides_control_automation(tmp_path: Path) -> None:
    """Range rules and exact overrides should keep archived versions stable."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        _replace_version_policy(
            config_path.read_text(encoding="utf-8"),
            """
version_policy:
  defaults:
    state: active
    refresh: artifact
    migrate_into: auto
    publish_release: true
  rules:
    - match: ">=v1.29.1 <v1.30.0"
      state: maintenance
      refresh: manual
      migrate_into: manual
      publish_release: true
    - match: ">=v1.30.0"
      state: active
      refresh: artifact
      migrate_into: auto
      publish_release: true
  overrides:
    v1.30.0:
      state: archived
      refresh: false
      migrate_into: false
      publish_release: false
      reason: frozen after depositar publication

""",
        ).replace(
            "    - v1.30.0\n    - v1.30.1",
            "    - v1.29.1\n    - v1.30.0\n    - v1.30.1",
        ),
        encoding="utf-8",
    )

    config = load_translation_repository_config(config_path)

    assert version_policy_decision(config, "v1.29.1").state == "maintenance"
    assert version_policy_decision(config, "v1.29.1").refresh == "manual"
    assert version_policy_allows_manual_refresh(config, "v1.29.1") is True
    assert version_policy_allows_auto_refresh(config, "v1.29.1") is False
    assert version_policy_allows_auto_migration(config, "v1.29.1") is False
    assert version_policy_allows_manual_migration(config, "v1.29.1") is True
    assert version_policy_decision(config, "v1.30.0").state == "archived"
    assert version_policy_decision(config, "v1.30.0").publish_release is False
    assert version_policy_allows_manual_migration(config, "v1.30.0") is False
    assert version_policy_decision(config, "v1.30.1").refresh == "artifact"
    assert version_policy_allows_auto_migration(config, "v1.30.1") is True
    assert target_versions(config, "v1.30.1") == []
    assert target_versions(config, "v1.30.1", ["v1.29.1"]) == ["v1.29.1"]
    with pytest.raises(TranslationRepositoryError, match="not allowed"):
        target_versions(config, "v1.30.1", ["v1.30.0"])


def test_version_policy_partial_layers_preserve_inherited_values(
    tmp_path: Path,
) -> None:
    """Later policy layers should change only fields they explicitly declare."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        _replace_version_policy(
            config_path.read_text(encoding="utf-8"),
            """
version_policy:
  defaults:
    state: available
    refresh: false
    migrate_into: false
    publish_release: false
    reason: not selected
  rules:
    - match: ">=v1.30.0"
      state: active
      refresh: artifact
      migrate_into: auto
      publish_release: true
      reason: active range
    - match: ">=v1.30.1"
      reason: latest active range
  overrides:
    v1.30.1:
      reason: preferred migration source

""",
        ),
        encoding="utf-8",
    )

    config = load_translation_repository_config(config_path)
    decision = version_policy_decision(config, "v1.30.1")

    assert decision.state == "active"
    assert decision.refresh == "artifact"
    assert decision.migrate_into == "auto"
    assert decision.publish_release is True
    assert decision.reason == "preferred migration source"


@pytest.mark.parametrize(
    ("field", "explicit_value"),
    [("refresh", "artifact"), ("migrate_into", "auto")],
)
def test_version_policy_rejects_ambiguous_true_shorthand(
    tmp_path: Path,
    field: str,
    explicit_value: str,
) -> None:
    """Enabling policy fields should use reviewable domain values, not true."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            f"    {field}: {explicit_value}",
            f"    {field}: true",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match=f"explicit value '{explicit_value}'"):
        load_translation_repository_config(config_path)


def test_version_policy_rejects_unknown_lifecycle_state(tmp_path: Path) -> None:
    """A state typo must not bypass published/archived mutation protection."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "    state: active",
            "    state: actvie",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="available, active, maintenance"):
        load_translation_repository_config(config_path)


@pytest.mark.parametrize("state", ["published", "archived"])
@pytest.mark.parametrize("refresh", ["artifact", "manual"])
def test_frozen_versions_cannot_refresh_from_artifacts(
    tmp_path: Path,
    state: str,
    refresh: str,
) -> None:
    """Published and archived versions should never mutate during sync refreshes."""

    config_path = _write_config(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "state: active\n    refresh: artifact",
            f"state: {state}\n    refresh: {refresh}",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryError, match="must use refresh=false"):
        load_translation_repository_config(config_path)


def test_version_policy_range_parser_supports_plus_and_comparators() -> None:
    """Policy ranges should be explicit but compact enough for long-lived repos."""

    assert version_matches_range("v1.30.2", ">=v1.30.0")
    assert version_matches_range("v1.30.2", "v1.30.0+")
    assert version_matches_range("v1.29.1", ">=v1.29.1 <v1.30.0")
    assert not version_matches_range("v1.30.0", ">=v1.29.1 <v1.30.0")


def test_version_to_number_requires_v_prefix() -> None:
    """Version branch tags should stay unambiguous."""

    assert version_to_number("v1.30.1") == "1.30.1"
    assert sorted_versions(["v1.30.10", "v1.30.2", "v1.30.1"]) == [
        "v1.30.1",
        "v1.30.2",
        "v1.30.10",
    ]
    with pytest.raises(TranslationRepositoryError):
        version_to_number("1.30.1")


def test_preview_runtime_for_version_matches_supported_metamodels() -> None:
    """Template versions should map to the DSW stack that supports their metamodel."""

    loaded_runtimes = load_preview_runtimes()

    assert loaded_runtimes[0].metamodel_key == "17-1"
    assert preview_runtime_for_version("v1.29.1").dsw_version == "4.26"
    assert preview_runtime_for_version("v1.29.1").tdk_version == "4.26.1"
    assert preview_runtime_for_version("v1.29.1").strict_project_preview is True
    assert preview_runtime_for_version("v1.30.0").metamodel_version == "18.0"
    assert preview_runtime_for_template("v1.30.0", "18.0").metamodel_key == "18-0"
    assert preview_runtime_for_version("v1.30.9").dsw_version == "4.30"
    assert preview_runtime_matrix()[0]["upstream_template_artifact_refs"] == "v1.29.1"
    assert preview_runtime_matrix()[0]["strict_project_preview"] == "true"
    assert preview_runtime_matrix()[-1]["upstream_template_artifact_refs"] == "v1.30.0+"
    assert preview_runtime_matrix()[-1]["strict_project_preview"] == "true"
    with pytest.raises(TranslationRepositoryError):
        preview_runtime_for_version("v1.29.0")
    with pytest.raises(TranslationRepositoryError):
        preview_runtime_for_template("v1.30.0", "19.0")
