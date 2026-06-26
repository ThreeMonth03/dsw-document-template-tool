"""Public README rendering for translated document template outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_public_output_readme(*, output_dir: Path, target_lang: str) -> None:
    """Replace the internal workspace README with public template documentation."""

    output_dir = Path(output_dir)
    template_json_path = output_dir / "template.json"
    if not template_json_path.is_file():
        return

    payload = json.loads(template_json_path.read_text(encoding="utf-8"))
    readme_path = output_dir / "README.md"
    readme_path.write_text(
        _render_public_readme(payload=payload, target_lang=target_lang),
        encoding="utf-8",
    )


def _render_public_readme(*, payload: dict[str, Any], target_lang: str) -> str:
    name = str(payload.get("name") or payload.get("templateId") or "Document Template")
    organization_id = str(payload.get("organizationId") or "")
    template_id = str(payload.get("templateId") or "")
    version = str(payload.get("version") or "")
    full_id = ":".join(part for part in [organization_id, template_id, version] if part)
    description = str(payload.get("description") or "").strip()

    lines = [
        f"# {name}",
        "",
        "This is a Traditional Chinese (zh-Hant) localization of the Science Europe "
        "DMP Template for Data Stewardship Wizard.",
    ]
    if description:
        lines.extend(["", description])
    if full_id:
        lines.extend(["", f"Template ID: `{full_id}`"])
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- Language: `{target_lang}`.",
            "- The original upstream README is preserved as `UPSTREAM-README.md` when available.",
            "- This package is intended for DSW document template import.",
        ]
    )
    return "\n".join(lines) + "\n"
