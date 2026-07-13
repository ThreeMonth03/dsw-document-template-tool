"""Tests for strict repository YAML loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsw_document_template_tool.yaml_config import (
    YamlConfigError,
    load_yaml_file,
    load_yaml_text,
)


def test_load_yaml_text_preserves_normal_mappings() -> None:
    """Valid configuration should retain ordinary safe-load behavior."""

    assert load_yaml_text("enabled: true\nitems:\n  - one\n") == {
        "enabled": True,
        "items": ["one"],
    }


def test_load_yaml_text_rejects_duplicate_nested_keys() -> None:
    """A repeated key must not silently replace an earlier policy value."""

    with pytest.raises(YamlConfigError, match="duplicate key 'refresh'"):
        load_yaml_text(
            "version_policy:\n  defaults:\n    refresh: artifact\n    refresh: false\n",
            source="translation-config.yml",
        )


def test_load_yaml_file_reports_source_path(tmp_path: Path) -> None:
    """Malformed file diagnostics should identify the config being loaded."""

    config_path = tmp_path / "broken.yml"
    config_path.write_text("items: [\n", encoding="utf-8")

    with pytest.raises(YamlConfigError, match=str(config_path)):
        load_yaml_file(config_path)
