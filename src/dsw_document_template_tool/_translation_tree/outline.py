"""Outline rendering for translator-facing translation trees."""

from __future__ import annotations

import os
from pathlib import Path

from .document import parse_sentence_text, parse_translation_document
from .manifest import TREE_MANIFEST_PATH, load_tree_manifest
from .models import OutlineUnit, TranslationTreeError


def refresh_outline_markdown(
    *,
    tree_dir: Path,
    source_lang: str,
    target_lang: str,
) -> Path:
    """Rewrite the tree outline from the current translation documents."""

    tree_dir = Path(tree_dir).resolve()
    output_outline = tree_dir / "outline.md"
    output_outline.write_text(
        render_outline_markdown(
            outline_units=load_outline_units(
                tree_dir=tree_dir,
                source_lang=source_lang,
                target_lang=target_lang,
            ),
            output_outline=output_outline,
        ),
        encoding="utf-8",
    )
    return output_outline


def load_outline_units(
    *,
    tree_dir: Path,
    source_lang: str,
    target_lang: str,
) -> list[OutlineUnit]:
    """Load outline rows from the tree manifest and current translation blocks."""

    tree_dir = Path(tree_dir).resolve()
    manifest = load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )

    outline_units: list[OutlineUnit] = []
    for unit in units:
        outline_units.append(
            _outline_unit_from_manifest_entry(
                tree_dir=tree_dir,
                unit=unit,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        )
    return outline_units


def render_outline_markdown(
    *,
    outline_units: list[OutlineUnit],
    output_outline: Path,
) -> str:
    """Render a clickable progress outline for translation units."""

    lines = ["### DSW Document Template Translation", ""]
    for source_file in sorted({unit.source_file for unit in outline_units}):
        file_units = [unit for unit in outline_units if unit.source_file == source_file]
        lines.append(
            _render_outline_checkbox_line(
                depth=0,
                is_complete=_all_translated(file_units),
                layer_label="[file]",
                label=f"{source_file} ({_progress_label(file_units)})",
            )
        )
        lines.append("")
        lines.append(f"  [J2] `{source_file}`")
        lines.append("")

        wrapper_orders = sorted({unit.wrapper_order for unit in file_units})
        for wrapper_order in wrapper_orders:
            wrapper_units = [unit for unit in file_units if unit.wrapper_order == wrapper_order]
            wrapper = wrapper_units[0]
            lines.append(
                _render_outline_checkbox_line(
                    depth=1,
                    is_complete=_all_translated(wrapper_units),
                    layer_label="[wrapper]",
                    label=f"{wrapper.wrapper_folder_name} ({_progress_label(wrapper_units)})",
                )
            )
            lines.append("")
            lines.append(f"      [W] `{wrapper.wrapper_folder_name}`")
            lines.append("")

            for unit in wrapper_units:
                relative_link = os.path.relpath(unit.document_path, output_outline.parent)
                formatted_link = _format_link_destination(relative_link)
                lines.append(
                    _render_outline_checkbox_line(
                        depth=2,
                        is_complete=unit.is_translated,
                        layer_label="[unit]",
                        label=f"{unit.unit_folder_name}: {unit.sentence_text}",
                    )
                )
                lines.append("")
                lines.append(f"          [T] [translation]({formatted_link})")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_outline_checkbox_line(
    *,
    depth: int,
    is_complete: bool,
    layer_label: str,
    label: str,
) -> str:
    indent = "    " * depth
    checkbox = "x" if is_complete else " "
    return f"{indent}- [{checkbox}] {layer_label} {label}"


def _all_translated(units: list[OutlineUnit]) -> bool:
    return bool(units) and all(unit.is_translated for unit in units)


def _progress_label(units: list[OutlineUnit]) -> str:
    translated = sum(1 for unit in units if unit.is_translated)
    return f"{translated}/{len(units)}"


def _format_link_destination(destination: str) -> str:
    escaped = destination.replace(">", "\\>")
    return f"<{escaped}>"


def _outline_unit_from_manifest_entry(
    *,
    tree_dir: Path,
    unit: object,
    source_lang: str,
    target_lang: str,
) -> OutlineUnit:
    if not isinstance(unit, dict):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
        )

    source_file = unit.get("source_file")
    wrapper_order = unit.get("wrapper_order")
    wrapper_folder_name = unit.get("wrapper_folder_name")
    unit_folder_name = unit.get("unit_folder_name")
    document_path_raw = unit.get("document_path")
    if (
        not isinstance(source_file, str)
        or not isinstance(wrapper_order, int)
        or not isinstance(wrapper_folder_name, str)
        or not isinstance(unit_folder_name, str)
        or not isinstance(document_path_raw, str)
    ):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
        )

    document_path = tree_dir / document_path_raw
    if not document_path.is_file():
        raise TranslationTreeError(f"Missing translation document at {document_path}")

    return OutlineUnit(
        source_file=source_file,
        wrapper_order=wrapper_order,
        wrapper_folder_name=wrapper_folder_name,
        unit_folder_name=unit_folder_name,
        document_path=document_path,
        sentence_text=parse_sentence_text(
            document_path=document_path,
            source_lang=source_lang,
        ),
        is_translated=bool(
            parse_translation_document(
                document_path=document_path,
                source_lang=source_lang,
                target_lang=target_lang,
            ).strip()
        ),
    )
