"""Safe three-way XLIFF merge helpers for Weblate review branches."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

XLIFF_NS = "urn:oasis:names:tc:xliff:document:1.2"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("", XLIFF_NS)


@dataclass(frozen=True)
class XliffUnit:
    """Text fields needed to compare one XLIFF translation unit."""

    source: str
    target: str


@dataclass(frozen=True)
class XliffMergeReport:
    """Summary of one Weblate-to-translation XLIFF reconciliation."""

    applied_units: int
    conflicted_units: int
    missing_review_units: int
    source_mismatch_units: int
    unchanged_units: int

    @property
    def changed(self) -> bool:
        """Return whether the merged XLIFF imports any Weblate edits."""

        return self.applied_units > 0


def merge_weblate_xliff_targets(
    *,
    current_xliff: Path,
    review_xliff: Path,
    output_xliff: Path,
    base_xliff: Path | None = None,
) -> XliffMergeReport:
    """Merge Weblate review targets into the current XLIFF safely.

    The current XLIFF is the generated exchange file for the checked-out
    ``translation/v*`` branch. It is used as the output skeleton so source
    hashes, notes, and current tree shape stay valid. Weblate target text is
    copied only when the same unit did not also change in ``translation/v*``.
    Same-unit conflicts keep the current translation branch value.
    """

    current_tree = ET.parse(current_xliff)
    current_root = current_tree.getroot()
    current_units = collect_units(current_root)
    review_units = collect_units(ET.parse(review_xliff).getroot())
    base_units = collect_units(ET.parse(base_xliff).getroot()) if base_xliff else {}

    applied_units = 0
    conflicted_units = 0
    missing_review_units = 0
    source_mismatch_units = 0
    unchanged_units = 0

    for trans_unit in iter_trans_units(current_root):
        unit_id = trans_unit.attrib["id"]
        current_unit = current_units[unit_id]
        review_unit = review_units.get(unit_id)
        if review_unit is None:
            missing_review_units += 1
            continue

        if review_unit.source != current_unit.source:
            source_mismatch_units += 1
            continue

        base_unit = base_units.get(unit_id)
        base_target = (
            base_unit.target
            if base_unit is not None and base_unit.source == current_unit.source
            else current_unit.target
        )

        if review_unit.target == base_target:
            unchanged_units += 1
            continue

        if current_unit.target in {base_target, review_unit.target}:
            set_target_text(trans_unit, review_unit.target)
            if review_unit.target != current_unit.target:
                applied_units += 1
            else:
                unchanged_units += 1
            continue

        conflicted_units += 1

    output_xliff.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(current_root, space="  ")
    payload = ET.tostring(current_root, encoding="utf-8", xml_declaration=False)
    output_xliff.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + payload + b"\n")

    return XliffMergeReport(
        applied_units=applied_units,
        conflicted_units=conflicted_units,
        missing_review_units=missing_review_units,
        source_mismatch_units=source_mismatch_units,
        unchanged_units=unchanged_units,
    )


def collect_units(root: ET.Element) -> dict[str, XliffUnit]:
    """Collect XLIFF units by id."""

    units: dict[str, XliffUnit] = {}
    for trans_unit in iter_trans_units(root):
        unit_id = trans_unit.attrib.get("id")
        if not unit_id:
            continue
        units[unit_id] = XliffUnit(
            source=child_text(trans_unit, "source"),
            target=child_text(trans_unit, "target"),
        )
    return units


def iter_trans_units(root: ET.Element) -> list[ET.Element]:
    """Return all trans-unit elements in document order."""

    return [element for element in root.iter() if local_name(element.tag) == "trans-unit"]


def child_text(trans_unit: ET.Element, child_name: str) -> str:
    """Return text from one direct child element."""

    matches = [child for child in trans_unit if local_name(child.tag) == child_name]
    if not matches:
        return ""
    return matches[0].text or ""


def set_target_text(trans_unit: ET.Element, target_text: str) -> None:
    """Set target text and keep Weblate state aligned with content."""

    matches = [child for child in trans_unit if local_name(child.tag) == "target"]
    if matches:
        target = matches[0]
    else:
        target = ET.SubElement(
            trans_unit,
            namespaced_tag(trans_unit.tag, "target"),
            {xml_attr("space"): "preserve"},
        )
    target.text = target_text
    target.attrib["state"] = "translated" if target_text.strip() else "new"


def namespaced_tag(reference_tag: str, local: str) -> str:
    """Return ``local`` in the same namespace as ``reference_tag``."""

    if reference_tag.startswith("{"):
        namespace = reference_tag.split("}", 1)[0].lstrip("{")
        return f"{{{namespace}}}{local}"
    return local


def xml_attr(name: str) -> str:
    """Return an XML namespace attribute name."""

    return f"{{{XML_NS}}}{name}"


def local_name(tag: str) -> str:
    """Return a tag without its XML namespace."""

    return tag.rsplit("}", 1)[-1]
