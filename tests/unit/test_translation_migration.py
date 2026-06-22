"""Tests for cross-version translation migration helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsw_document_template_tool.translation_migration import (
    TranslationMigrationError,
    load_translation_repository_config,
    migration_branch,
    target_versions,
    version_branch,
    version_paths,
    version_to_number,
)


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "translation-config.yml"
    config_path.write_text(
        """
schema_version: 1

template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: https://github.com/ds-wizard/science-europe-template.git
  supported_versions:
    - v1.30.0
    - v1.30.1

translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant
  translated_template_organization_id: dsw
  translated_template_id: science-europe-zh-hant
  translated_template_name: Science Europe DMP Template (zh-Hant)

branches:
  version_branch_prefix: translation/

tooling:
  repository: ThreeMonth03/DSW-document-template-tool
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


def test_load_translation_repository_config_and_paths(tmp_path: Path) -> None:
    """The migration config should derive stable version-specific paths."""

    config = load_translation_repository_config(_write_config(tmp_path))
    paths = version_paths(config, "v1.30.1")

    assert config.template.supported_versions == ("v1.30.0", "v1.30.1")
    assert version_branch(config, "v1.30.1") == "translation/v1.30.1"
    assert migration_branch(config, "v1.30.0", "v1.30.1") == (
        "automation/migrate-v1.30.0-to-v1.30.1"
    )
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


def test_target_versions_excludes_source_and_validates_targets(tmp_path: Path) -> None:
    """Migration targets should be explicit supported versions, excluding the source."""

    config = load_translation_repository_config(_write_config(tmp_path))

    assert target_versions(config, "v1.30.0") == ["v1.30.1"]
    assert target_versions(config, "v1.30.0", ["v1.30.0", "v1.30.1"]) == ["v1.30.1"]
    with pytest.raises(TranslationMigrationError):
        target_versions(config, "v1.30.0", ["v9.99.9"])


def test_version_to_number_requires_v_prefix() -> None:
    """Version branch tags should stay unambiguous."""

    assert version_to_number("v1.30.1") == "1.30.1"
    with pytest.raises(TranslationMigrationError):
        version_to_number("1.30.1")
