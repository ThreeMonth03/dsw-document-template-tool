"""Outline rendering for translator-facing translation trees."""

from __future__ import annotations

import os
from pathlib import Path

from .models import OutlineUnit


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
