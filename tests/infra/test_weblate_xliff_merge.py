"""Tests for safe Weblate XLIFF reconciliation."""

from __future__ import annotations

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def load_merge_module(repo_root: Path):
    """Load the XLIFF merge helper as a module."""

    module_path = repo_root / "scripts" / "ci" / "_weblate_xliff_merge.py"
    spec = importlib.util.spec_from_file_location("_weblate_xliff_merge", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_merge_weblate_xliff_targets_applies_only_safe_units(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Weblate edits should not overwrite same-unit translation branch edits."""

    module = load_merge_module(repo_root)
    base = tmp_path / "base.xlf"
    current = tmp_path / "current.xlf"
    review = tmp_path / "review.xlf"
    output = tmp_path / "output.xlf"

    base.write_text(
        render_xliff(
            {
                "a": ("A source", "A base"),
                "b": ("B source", "B base"),
                "c": ("C source", "C base"),
                "d": ("D source", "D base"),
            },
        ),
        encoding="utf-8",
    )
    current.write_text(
        render_xliff(
            {
                "a": ("A source", "A base"),
                "b": ("B source", "B translation branch"),
                "c": ("C source", "C translation branch"),
                "d": ("D source changed", "D translation branch"),
            },
        ),
        encoding="utf-8",
    )
    review.write_text(
        render_xliff(
            {
                "a": ("A source", "A Weblate"),
                "b": ("B source", "B base"),
                "c": ("C source", "C Weblate"),
                "d": ("D source", "D Weblate"),
                "obsolete": ("Old source", "Old target"),
            },
        ),
        encoding="utf-8",
    )

    report = module.merge_weblate_xliff_targets(
        current_xliff=current,
        review_xliff=review,
        base_xliff=base,
        output_xliff=output,
    )

    assert report.applied_units == 1
    assert report.conflicted_units == 1
    assert report.source_mismatch_units == 1
    assert collect_targets(output) == {
        "a": "A Weblate",
        "b": "B translation branch",
        "c": "C translation branch",
        "d": "D translation branch",
    }


def render_xliff(units: dict[str, tuple[str, str]]) -> str:
    """Render a tiny XLIFF file for tests."""

    body = "\n".join(
        f"""      <trans-unit id="{unit_id}" xml:space="preserve">
        <source xml:space="preserve">{source}</source>
        <target xml:space="preserve" state="translated">{target}</target>
      </trans-unit>"""
        for unit_id, (source, target) in units.items()
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xliff xmlns="urn:oasis:names:tc:xliff:document:1.2" version="1.2">
  <file original="tree" datatype="plaintext" source-language="en" target-language="zh_Hant">
    <body>
{body}
    </body>
  </file>
</xliff>
"""


def collect_targets(xliff_path: Path) -> dict[str, str]:
    """Collect target text by unit id."""

    root = ET.parse(xliff_path).getroot()
    targets: dict[str, str] = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "trans-unit":
            continue
        unit_id = element.attrib["id"]
        target = next(child for child in element if child.tag.rsplit("}", 1)[-1] == "target")
        targets[unit_id] = target.text or ""
    return targets
