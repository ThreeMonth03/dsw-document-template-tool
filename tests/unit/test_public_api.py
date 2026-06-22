"""Public import compatibility tests for downstream workflow repositories."""

from __future__ import annotations

import dsw_document_template_tool as toolkit
from dsw_document_template_tool import translation_tree
from dsw_document_template_tool.render_project import (
    build_argument_parser as build_render_project_parser,
)
from dsw_document_template_tool.render_project import render_project


def test_root_package_exports_translation_workflow_api() -> None:
    """Downstream repos should be able to import the stable workflow helpers."""

    expected_exports = {
        "TranslationMergeReport",
        "TranslationTreeError",
        "audit_translated_template_structure",
        "audit_translation_tree",
        "compact_template_dir",
        "expand_template_dir",
        "export_translation_tree",
        "merge_translation_tree",
        "snapshot_tree",
        "sync_translation_tree",
    }

    assert expected_exports.issubset(set(toolkit.__all__))
    for name in expected_exports:
        assert getattr(toolkit, name) is not None


def test_translation_tree_module_exports_merge_api() -> None:
    """The translation-tree submodule should expose merge/migration helpers."""

    expected_exports = {
        "TranslationMergeReport",
        "TranslationTreeError",
        "audit_translated_template_structure",
        "audit_translation_tree",
        "export_translation_tree",
        "merge_translation_tree",
        "sync_translation_tree",
    }

    assert expected_exports.issubset(set(translation_tree.__all__))
    assert translation_tree.merge_translation_tree is toolkit.merge_translation_tree
    assert translation_tree.TranslationMergeReport is toolkit.TranslationMergeReport


def test_render_project_logic_is_importable_from_package_module() -> None:
    """The root CLI shim should not be the only import path for render-project logic."""

    parser = build_render_project_parser()

    assert callable(render_project)
    assert parser.prog
