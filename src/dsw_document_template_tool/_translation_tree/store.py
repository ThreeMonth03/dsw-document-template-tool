"""Load translator edits from a translation tree."""

from __future__ import annotations

from pathlib import Path

from .document import parse_translation_document
from .manifest import TREE_MANIFEST_PATH, load_tree_manifest
from .models import TranslationEntry, TranslationTreeError


def load_existing_translations(
    *,
    output_dir: Path,
    source_lang: str,
    target_lang: str,
) -> dict[tuple[str, str], str]:
    """Load reusable translations from an existing tree, ignoring broken files.

    Export uses this forgiving loader so that a regenerated tree can repair
    deleted or malformed Markdown skeletons without losing still-readable
    translator edits.
    """

    manifest_path = output_dir / TREE_MANIFEST_PATH
    if not manifest_path.is_file():
        return {}
    manifest = load_tree_manifest(output_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        return {}
    translations: dict[tuple[str, str], str] = {}
    for unit in units:
        source_file = unit.get("source_file")
        unit_key = unit.get("unit_key")
        document_path_raw = unit.get("document_path")
        if (
            not isinstance(source_file, str)
            or not isinstance(unit_key, str)
            or not isinstance(document_path_raw, str)
        ):
            continue
        document_path = output_dir / document_path_raw
        if not document_path.is_file():
            continue
        try:
            translation_text = parse_translation_document(
                document_path=document_path,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        except TranslationTreeError:
            continue
        translations[(source_file, unit_key)] = translation_text
    return translations


def load_translations_by_unit_key(
    *,
    tree_dir: Path,
    source_lang: str,
    target_lang: str,
) -> dict[tuple[str, str], TranslationEntry]:
    """Load translator edits from a tree, failing on broken required files."""

    manifest = load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )
    translations: dict[tuple[str, str], TranslationEntry] = {}
    for unit in units:
        source_file = unit.get("source_file")
        unit_key = unit.get("unit_key")
        document_path_raw = unit.get("document_path")
        if (
            not isinstance(source_file, str)
            or not isinstance(unit_key, str)
            or not isinstance(document_path_raw, str)
        ):
            raise TranslationTreeError(
                f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
            )
        document_path = tree_dir / document_path_raw
        if not document_path.is_file():
            raise TranslationTreeError(
                f"Missing translation document at {document_path}. "
                "Run `make export-translation-tree` to restore it."
            )
        translation_text = parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        translations[(source_file, unit_key)] = TranslationEntry(
            text=translation_text,
            document_path=document_path_raw,
        )
    return translations
