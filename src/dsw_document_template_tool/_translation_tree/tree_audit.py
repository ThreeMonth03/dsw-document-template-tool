"""Audit translator-facing tree files before syncing them."""

from __future__ import annotations

from pathlib import Path

from ..template_transform import GENERATED_BLOCK_PATTERN, generated_block_body
from .document import parse_translation_document
from .manifest import TREE_MANIFEST_PATH, load_tree_manifest
from .models import TranslationTreeAuditIssue, TranslationTreeError
from .placeholders import (
    build_source_placeholder_map,
    contains_raw_jinja_in_translation,
    source_placeholder_counts,
    validate_translation_placeholders,
)
from .source_text import (
    contains_jinja_block_or_comment,
    hard_fragment_sentence_message,
)
from .workspace import validate_expanded_workspace


def audit_translation_tree(
    *,
    tree_dir: Path,
    source_dir: Path,
    source_lang: str = "en",
    target_lang: str = "zh_Hant",
) -> list[TranslationTreeAuditIssue]:
    """Return structural issues that make translation blocks unsafe to edit."""

    tree_dir = Path(tree_dir).resolve()
    source_dir = Path(source_dir).resolve()
    issues: list[TranslationTreeAuditIssue] = []

    try:
        validate_expanded_workspace(source_dir)
    except TranslationTreeError as exc:
        return [
            TranslationTreeAuditIssue(
                code="invalid-expanded-workspace",
                location=str(source_dir),
                message=str(exc),
            )
        ]

    try:
        manifest = load_tree_manifest(tree_dir)
    except TranslationTreeError as exc:
        return [
            TranslationTreeAuditIssue(
                code="invalid-translation-tree",
                location=str(tree_dir),
                message=str(exc),
            )
        ]

    units = manifest.get("units")
    if not isinstance(units, list):
        return [
            TranslationTreeAuditIssue(
                code="invalid-translation-tree",
                location=str(tree_dir / TREE_MANIFEST_PATH),
                message="Manifest `units` must be a list.",
            )
        ]

    for unit in units:
        issues.extend(
            _audit_manifest_unit(
                tree_dir=tree_dir,
                source_dir=source_dir,
                unit=unit,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        )

    return issues


def _audit_manifest_unit(
    *,
    tree_dir: Path,
    source_dir: Path,
    unit: object,
    source_lang: str,
    target_lang: str,
) -> list[TranslationTreeAuditIssue]:
    issues: list[TranslationTreeAuditIssue] = []
    if not isinstance(unit, dict):
        return [
            TranslationTreeAuditIssue(
                code="invalid-manifest-unit",
                location=str(tree_dir / TREE_MANIFEST_PATH),
                message=f"Manifest unit must be an object, got {type(unit).__name__}.",
            )
        ]

    source_file = unit.get("source_file")
    unit_key = unit.get("unit_key")
    document_path_raw = unit.get("document_path")
    if not isinstance(source_file, str) or not isinstance(unit_key, str):
        return [
            TranslationTreeAuditIssue(
                code="invalid-manifest-unit",
                location=str(tree_dir / TREE_MANIFEST_PATH),
                message="Manifest unit is missing a valid source_file or unit_key.",
            )
        ]
    location = source_file if not isinstance(unit_key, str) else f"{source_file} ({unit_key})"

    try:
        source_unit_text = _source_unit_text_from_manifest_unit(
            source_dir=source_dir,
            unit=unit,
        )
    except TranslationTreeError as exc:
        issues.append(
            TranslationTreeAuditIssue(
                code="invalid-source-span",
                location=location,
                message=str(exc),
            )
        )
        source_unit_text = None

    if source_unit_text is not None:
        if contains_jinja_block_or_comment(source_unit_text):
            issues.append(
                TranslationTreeAuditIssue(
                    code="unsafe-source-jinja-block",
                    location=location,
                    message=(
                        "Source unit contains raw Jinja block/comment syntax. "
                        "Expand/export must split this before translators edit it."
                    ),
                )
            )

        hard_fragment_message = hard_fragment_sentence_message(source_unit_text)
        if hard_fragment_message is not None:
            issues.append(
                TranslationTreeAuditIssue(
                    code="hard-to-translate-source-fragment",
                    location=location,
                    message=hard_fragment_message,
                )
            )

        placeholder_map = build_source_placeholder_map(source_unit_text)
        source_placeholder_names = set(source_placeholder_counts(source_unit_text))
        ambiguous_names = sorted(source_placeholder_names - set(placeholder_map))
        if ambiguous_names:
            issues.append(
                TranslationTreeAuditIssue(
                    code="ambiguous-source-placeholder",
                    location=location,
                    message=(
                        "Source unit has placeholder names that cannot be mapped back "
                        f"unambiguously: {', '.join('{' + name + '}' for name in ambiguous_names)}"
                    ),
                )
            )

    if not isinstance(document_path_raw, str):
        issues.append(
            TranslationTreeAuditIssue(
                code="invalid-manifest-unit",
                location=location,
                message="Manifest unit is missing a valid document_path.",
            )
        )
        return issues

    document_path = tree_dir / document_path_raw
    if not document_path.is_file():
        issues.append(
            TranslationTreeAuditIssue(
                code="missing-translation-document",
                location=document_path_raw,
                message="Translation document is missing. Re-run export to restore it.",
            )
        )
        return issues

    try:
        translation_text = parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
    except TranslationTreeError as exc:
        issues.append(
            TranslationTreeAuditIssue(
                code="invalid-translation-document",
                location=document_path_raw,
                message=str(exc),
            )
        )
        return issues

    has_raw_jinja_translation = contains_raw_jinja_in_translation(translation_text)
    if has_raw_jinja_translation:
        issues.append(
            TranslationTreeAuditIssue(
                code="raw-jinja-in-translation",
                location=document_path_raw,
                message=(
                    "Translation block contains raw Jinja syntax. Use translator "
                    "placeholders such as `{name}` instead of `{% ... %}` or `{{ ... }}`."
                ),
            )
        )

    if source_unit_text is not None and translation_text.strip() and not has_raw_jinja_translation:
        try:
            validate_translation_placeholders(
                source_file=source_file,
                unit_key=unit_key,
                translation_document_path=document_path_raw,
                source_text=source_unit_text,
                translation_text=translation_text,
            )
        except TranslationTreeError as exc:
            issues.append(
                TranslationTreeAuditIssue(
                    code="invalid-translation-placeholders",
                    location=document_path_raw,
                    message=str(exc),
                )
            )

    return issues


def _source_unit_text_from_manifest_unit(*, source_dir: Path, unit: dict) -> str:
    source_file = unit.get("source_file")
    wrapper_order = unit.get("wrapper_order")
    unit_start = unit.get("unit_start")
    unit_end = unit.get("unit_end")
    if (
        not isinstance(source_file, str)
        or not isinstance(wrapper_order, int)
        or not isinstance(unit_start, int)
        or not isinstance(unit_end, int)
    ):
        raise TranslationTreeError("Manifest unit has invalid source span metadata.")

    source_path = source_dir / source_file
    if not source_path.is_file():
        raise TranslationTreeError(f"Source file is missing: {source_path}")
    source_text = source_path.read_text(encoding="utf-8")
    wrappers = list(GENERATED_BLOCK_PATTERN.finditer(source_text))
    if wrapper_order < 1 or wrapper_order > len(wrappers):
        raise TranslationTreeError(
            f"Wrapper order {wrapper_order} does not exist in {source_file}."
        )
    wrapper_body = generated_block_body(wrappers[wrapper_order - 1])
    if unit_start < 0 or unit_end > len(wrapper_body) or unit_start >= unit_end:
        raise TranslationTreeError(
            f"Unit span {unit_start}:{unit_end} is invalid for {source_file}."
        )
    return wrapper_body[unit_start:unit_end]
