"""Translator-facing tree export and sync for expanded DSW templates."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ._template_transform.markers import (
    GENERATED_BLOCK_PATTERN,
    generated_block_body,
    generated_block_name,
)
from ._translation_tree.apply import apply_unit_translations
from ._translation_tree.document import (
    TRANSLATION_DOC_NAME,
    render_translation_document,
    render_tree_readme,
)
from ._translation_tree.extraction import (
    extract_units as _extract_units,
)
from ._translation_tree.extraction import (
    wrap_translatable_block,
)
from ._translation_tree.filesystem import reset_dir
from ._translation_tree.ids import hash_text
from ._translation_tree.manifest import (
    TREE_MANIFEST_PATH,
    TREE_VERSION,
    load_tree_manifest,
)
from ._translation_tree.merge import (
    TranslationMergeReport,
    merge_translation_tree,
)
from ._translation_tree.metadata import patch_template_metadata
from ._translation_tree.models import (
    OutlineUnit,
    TranslationTreeError,
)
from ._translation_tree.outline import render_outline_markdown
from ._translation_tree.output_polish import polish_translated_output_dir
from ._translation_tree.source_text import (
    extract_sentence_text as _extract_sentence_text,
)
from ._translation_tree.store import (
    load_existing_translations,
    load_translations_by_unit_key,
)
from ._translation_tree.structure_audit import (
    audit_translated_template_structure as audit_translated_template_structure,
)
from ._translation_tree.tree_audit import audit_translation_tree as audit_translation_tree
from ._translation_tree.workspace import validate_expanded_workspace

TREE_ROOT_NAME = "tree"
DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "zh_Hant"
__all__ = [
    "DEFAULT_SOURCE_LANG",
    "DEFAULT_TARGET_LANG",
    "TREE_ROOT_NAME",
    "TranslationMergeReport",
    "TranslationTreeError",
    "audit_translated_template_structure",
    "audit_translation_tree",
    "export_translation_tree",
    "merge_translation_tree",
    "sync_translation_tree",
]


def export_translation_tree(
    *,
    source_dir: Path,
    output_dir: Path,
    source_lang: str = DEFAULT_SOURCE_LANG,
    target_lang: str = DEFAULT_TARGET_LANG,
) -> Path:
    """Export one expanded template workspace into translator-facing unit files."""

    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    validate_expanded_workspace(source_dir)
    existing_translations = load_existing_translations(
        output_dir=output_dir,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    reset_dir(output_dir)
    tree_root = output_dir / TREE_ROOT_NAME
    tree_root.mkdir(parents=True, exist_ok=True)

    manifest_units: list[dict[str, str | int]] = []
    outline_units: list[OutlineUnit] = []

    for source_path in sorted(source_dir.rglob("*.j2")):
        relative_path = source_path.relative_to(source_dir)
        relative_posix = relative_path.as_posix()
        source_text = source_path.read_text(encoding="utf-8")
        units = _extract_units(relative_path=relative_posix, source_text=source_text)
        if not units:
            continue

        for unit in units:
            translation_text = existing_translations.get((unit.source_file, unit.unit_key), "")
            doc_dir = tree_root / relative_path / unit.wrapper_folder_name / unit.unit_folder_name
            doc_dir.mkdir(parents=True, exist_ok=True)
            document_path = doc_dir / TRANSLATION_DOC_NAME
            document_path.write_text(
                render_translation_document(
                    unit=unit,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    sentence_text=_extract_sentence_text(unit.source_text),
                    translation_text=translation_text,
                ),
                encoding="utf-8",
            )
            manifest_units.append(
                {
                    "source_file": unit.source_file,
                    "wrapper_name": unit.wrapper_name,
                    "wrapper_order": unit.wrapper_order,
                    "wrapper_key": unit.wrapper_key,
                    "wrapper_folder_name": unit.wrapper_folder_name,
                    "wrapper_source_hash": unit.wrapper_source_hash,
                    "unit_order": unit.unit_order,
                    "unit_key": unit.unit_key,
                    "unit_folder_name": unit.unit_folder_name,
                    "unit_source_hash": unit.unit_source_hash,
                    "unit_start": unit.unit_start,
                    "unit_end": unit.unit_end,
                    "document_path": document_path.relative_to(output_dir).as_posix(),
                }
            )

            outline_units.append(
                OutlineUnit(
                    source_file=unit.source_file,
                    wrapper_order=unit.wrapper_order,
                    wrapper_folder_name=unit.wrapper_folder_name,
                    unit_folder_name=unit.unit_folder_name,
                    document_path=document_path,
                    sentence_text=_extract_sentence_text(unit.source_text),
                    is_translated=bool(translation_text.strip()),
                )
            )

    (output_dir / "README.md").write_text(
        render_tree_readme(
            source_lang=source_lang,
            target_lang=target_lang,
        ),
        encoding="utf-8",
    )
    (output_dir / "outline.md").write_text(
        render_outline_markdown(
            outline_units=outline_units,
            output_outline=output_dir / "outline.md",
        ),
        encoding="utf-8",
    )

    manifest_path = output_dir / TREE_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": TREE_VERSION,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "units": manifest_units,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_dir


def sync_translation_tree(
    *,
    tree_dir: Path,
    source_dir: Path,
    output_dir: Path,
    source_lang: str = DEFAULT_SOURCE_LANG,
    target_lang: str = DEFAULT_TARGET_LANG,
    template_organization_id: str | None = None,
    template_id: str | None = None,
    template_name: str | None = None,
    template_version: str | None = None,
) -> Path:
    """Apply translator-edited unit files back to one expanded workspace copy."""

    tree_dir = Path(tree_dir).resolve()
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    validate_expanded_workspace(source_dir)
    manifest = load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )

    translations = load_translations_by_unit_key(
        tree_dir=tree_dir,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    units_by_file: dict[str, list[dict[str, str | int]]] = {}
    for unit in units:
        source_file = unit["source_file"]
        if not isinstance(source_file, str):
            raise TranslationTreeError(
                f"Invalid source_file in translation-tree manifest: {source_file!r}"
            )
        units_by_file.setdefault(source_file, []).append(unit)

    translated_files: dict[str, str] = {}
    for source_file, file_units in units_by_file.items():
        source_path = source_dir / source_file
        source_text = source_path.read_text(encoding="utf-8")
        wrapper_matches = list(GENERATED_BLOCK_PATTERN.finditer(source_text))

        units_by_wrapper: dict[int, list[dict[str, str | int]]] = {}
        for unit in file_units:
            wrapper_order = unit["wrapper_order"]
            if not isinstance(wrapper_order, int):
                raise TranslationTreeError(
                    f"Invalid wrapper_order in translation-tree manifest: {wrapper_order!r}"
                )
            units_by_wrapper.setdefault(wrapper_order, []).append(unit)

        rebuilt_parts: list[str] = []
        cursor = 0
        for wrapper_order, match in enumerate(wrapper_matches, start=1):
            rebuilt_parts.append(source_text[cursor : match.start()])

            wrapper_units = units_by_wrapper.get(wrapper_order)
            if not wrapper_units:
                rebuilt_parts.append(match.group(0))
                cursor = match.end()
                continue

            wrapper_name = generated_block_name(match)
            first_unit = wrapper_units[0]
            expected_wrapper_name = first_unit["wrapper_name"]
            if not isinstance(expected_wrapper_name, str) or wrapper_name != expected_wrapper_name:
                raise TranslationTreeError(
                    "Wrapper mismatch while syncing translation tree for "
                    f"{source_file}: expected {expected_wrapper_name}, found {wrapper_name}"
                )

            wrapper_body = generated_block_body(match)
            wrapper_hash = hash_text(wrapper_body)
            expected_wrapper_hash = first_unit["wrapper_source_hash"]
            if not isinstance(expected_wrapper_hash, str) or wrapper_hash != expected_wrapper_hash:
                raise TranslationTreeError(
                    "Expanded source wrapper changed since the translation tree was exported for "
                    f"{source_file} ({first_unit['wrapper_folder_name']}). Re-run "
                    "`make export-translation-tree`."
                )

            rebuilt_parts.append(
                wrap_translatable_block(
                    wrapper_name,
                    apply_unit_translations(
                        source_file=source_file,
                        wrapper_body=wrapper_body,
                        wrapper_units=wrapper_units,
                        translations=translations,
                    ),
                )
            )
            cursor = match.end()

        unknown_wrapper_orders = [
            wrapper_order
            for wrapper_order in units_by_wrapper
            if wrapper_order < 1 or wrapper_order > len(wrapper_matches)
        ]
        if unknown_wrapper_orders:
            raise TranslationTreeError(
                "Translation tree references wrapper orders that do not exist in "
                f"{source_file}: {unknown_wrapper_orders}"
            )

        rebuilt_parts.append(source_text[cursor:])
        translated_files[source_file] = "".join(rebuilt_parts)

    reset_dir(output_dir)
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)
    for source_file, translated_text in translated_files.items():
        (output_dir / source_file).write_text(translated_text, encoding="utf-8")
    patch_template_metadata(
        output_dir=output_dir,
        organization_id=template_organization_id,
        template_id=template_id,
        name=template_name,
        version=template_version,
    )
    polish_translated_output_dir(output_dir=output_dir, target_lang=target_lang)

    return output_dir
