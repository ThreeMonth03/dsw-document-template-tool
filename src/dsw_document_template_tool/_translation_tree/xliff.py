"""XLIFF exchange helpers for Weblate-style translation workflows."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .document import (
    parse_sentence_text,
    parse_translation_document,
    replace_translation_text,
)
from .manifest import TREE_MANIFEST_PATH, load_tree_manifest
from .models import TranslationTreeError
from .outline import refresh_outline_markdown

XLIFF_NS = "urn:oasis:names:tc:xliff:document:1.2"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("", XLIFF_NS)


@dataclass(frozen=True)
class WeblateImportReport:
    """Summary of one XLIFF import into a translation tree."""

    imported_units: int


def export_weblate_xliff(
    *,
    tree_dir: Path,
    output_path: Path,
    source_lang: str,
    target_lang: str,
) -> Path:
    """Export a translation tree to one XLIFF 1.2 file for Weblate."""

    tree_dir = Path(tree_dir).resolve()
    output_path = Path(output_path).resolve()
    manifest = load_tree_manifest(tree_dir)
    units = _manifest_units(manifest, tree_dir=tree_dir)

    root = ET.Element(_tag("xliff"), {"version": "1.2"})
    file_element = ET.SubElement(
        root,
        _tag("file"),
        {
            "original": tree_dir.name,
            "datatype": "plaintext",
            "source-language": source_lang,
            "target-language": target_lang,
        },
    )
    body = ET.SubElement(file_element, _tag("body"))

    for unit in units:
        document_path_raw = _required_str(unit, "document_path")
        document_path = tree_dir / document_path_raw
        source_text = parse_sentence_text(
            document_path=document_path,
            source_lang=source_lang,
        )
        translation_text = parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        trans_unit = ET.SubElement(
            body,
            _tag("trans-unit"),
            {
                "id": document_path_raw,
                "resname": _required_str(unit, "unit_key"),
                _xml_attr("space"): "preserve",
            },
        )
        ET.SubElement(
            trans_unit,
            _tag("source"),
            {_xml_attr("space"): "preserve"},
        ).text = source_text
        ET.SubElement(
            trans_unit,
            _tag("target"),
            {
                _xml_attr("space"): "preserve",
                "state": "translated" if translation_text.strip() else "new",
            },
        ).text = translation_text
        for key in (
            "source_file",
            "wrapper_key",
            "unit_key",
            "unit_source_hash",
            "document_path",
        ):
            ET.SubElement(trans_unit, _tag("note"), {"from": key}).text = _required_str(
                unit,
                key,
            )

    ET.indent(root, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    output_path.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + payload + b"\n")
    return output_path


def import_weblate_xliff(
    *,
    tree_dir: Path,
    xliff_path: Path,
    source_lang: str,
    target_lang: str,
) -> WeblateImportReport:
    """Import Weblate-edited XLIFF targets back into a translation tree."""

    tree_dir = Path(tree_dir).resolve()
    xliff_path = Path(xliff_path).resolve()
    manifest = load_tree_manifest(tree_dir)
    units_by_document_path = {
        _required_str(unit, "document_path"): unit
        for unit in _manifest_units(manifest, tree_dir=tree_dir)
    }

    tree = ET.parse(xliff_path)
    root = tree.getroot()
    _validate_file_languages(
        root=root,
        xliff_path=xliff_path,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    seen_ids: set[str] = set()
    imported_units = 0
    for trans_unit in _iter_children(root, "trans-unit"):
        unit_id = trans_unit.attrib.get("id")
        if not unit_id:
            raise TranslationTreeError(f"XLIFF trans-unit is missing id in {xliff_path}")
        if unit_id in seen_ids:
            raise TranslationTreeError(f"Duplicate XLIFF trans-unit id in {xliff_path}: {unit_id}")
        seen_ids.add(unit_id)

        unit = units_by_document_path.get(unit_id)
        if unit is None:
            raise TranslationTreeError(
                f"XLIFF unit does not exist in the current translation tree: {unit_id}"
            )
        notes = _notes_by_from(trans_unit)
        expected_hash = _required_str(unit, "unit_source_hash")
        actual_hash = notes.get("unit_source_hash")
        if actual_hash != expected_hash:
            raise TranslationTreeError(
                "XLIFF unit source hash does not match the current translation tree "
                f"for {unit_id}: expected {expected_hash}, found {actual_hash or '<missing>'}"
            )

        document_path = tree_dir / unit_id
        source_text = _required_child_text(trans_unit, "source", unit_id=unit_id)
        current_source_text = parse_sentence_text(
            document_path=document_path,
            source_lang=source_lang,
        )
        if source_text != current_source_text:
            raise TranslationTreeError(
                f"XLIFF source text does not match the current translation document for {unit_id}"
            )

        translation_text = _optional_child_text(trans_unit, "target", unit_id=unit_id)
        replace_translation_text(
            document_path=document_path,
            target_lang=target_lang,
            translation_text=translation_text,
        )
        imported_units += 1

    refresh_outline_markdown(
        tree_dir=tree_dir,
        source_lang=source_lang,
        target_lang=target_lang,
    )
    return WeblateImportReport(imported_units=imported_units)


def _manifest_units(manifest: dict, *, tree_dir: Path) -> list[dict]:
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )
    for unit in units:
        if not isinstance(unit, dict):
            raise TranslationTreeError(
                f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
            )
    return units


def _required_str(unit: dict, key: str) -> str:
    value = unit.get(key)
    if not isinstance(value, str):
        raise TranslationTreeError(f"Manifest unit is missing a valid {key}.")
    return value


def _tag(name: str) -> str:
    return f"{{{XLIFF_NS}}}{name}"


def _xml_attr(name: str) -> str:
    return f"{{{XML_NS}}}{name}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_children(root: ET.Element, local_name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == local_name]


def _validate_file_languages(
    *,
    root: ET.Element,
    xliff_path: Path,
    source_lang: str,
    target_lang: str,
) -> None:
    file_elements = _iter_children(root, "file")
    if not file_elements:
        raise TranslationTreeError(f"XLIFF file has no file element: {xliff_path}")
    file_element = file_elements[0]
    actual_source_lang = file_element.attrib.get("source-language")
    actual_target_lang = file_element.attrib.get("target-language")
    if actual_source_lang != source_lang or actual_target_lang != target_lang:
        raise TranslationTreeError(
            "Unexpected XLIFF languages in "
            f"{xliff_path}: expected {source_lang}/{target_lang}, "
            f"found {actual_source_lang}/{actual_target_lang}"
        )


def _notes_by_from(trans_unit: ET.Element) -> dict[str, str]:
    notes: dict[str, str] = {}
    for child in trans_unit:
        if _local_name(child.tag) == "note":
            note_from = child.attrib.get("from")
            if note_from:
                notes[note_from] = child.text or ""
    return notes


def _required_child_text(trans_unit: ET.Element, local_name: str, *, unit_id: str) -> str:
    text = _optional_child_text(trans_unit, local_name, unit_id=unit_id)
    if text == "":
        raise TranslationTreeError(f"XLIFF unit {unit_id} is missing {local_name} text")
    return text


def _optional_child_text(trans_unit: ET.Element, local_name: str, *, unit_id: str) -> str:
    matches = [child for child in trans_unit if _local_name(child.tag) == local_name]
    if not matches:
        return ""
    if len(matches) > 1:
        raise TranslationTreeError(f"XLIFF unit {unit_id} has multiple {local_name} elements")
    element = matches[0]
    if list(element):
        raise TranslationTreeError(
            f"XLIFF unit {unit_id} contains nested XML inside {local_name}; "
            "use escaped text instead."
        )
    return element.text or ""
