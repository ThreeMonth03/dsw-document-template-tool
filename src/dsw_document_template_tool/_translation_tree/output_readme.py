"""Public README rendering for translated document template outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_public_output_readme(
    *,
    output_dir: Path,
    target_lang: str,
    public_readme_path: Path | None = None,
) -> None:
    """Replace the internal workspace README with public template documentation."""

    output_dir = Path(output_dir)
    readme_path = output_dir / "README.md"
    payload = _load_template_payload(output_dir)
    public_readme = Path(public_readme_path) if public_readme_path is not None else None
    if public_readme is not None and public_readme.is_file():
        readme_path.write_text(
            _render_configured_public_readme(
                public_readme.read_text(encoding="utf-8"),
                payload=payload,
            ),
            encoding="utf-8",
        )
        return

    if payload is None:
        return

    readme_path.write_text(
        _render_public_readme(payload=payload, target_lang=target_lang),
        encoding="utf-8",
    )


def _load_template_payload(output_dir: Path) -> dict[str, Any] | None:
    template_json_path = output_dir / "template.json"
    if not template_json_path.is_file():
        return None
    return json.loads(template_json_path.read_text(encoding="utf-8"))


def _render_configured_public_readme(
    content: str,
    *,
    payload: dict[str, Any] | None,
) -> str:
    if payload is None:
        return content

    organization_id = str(payload.get("organizationId") or "")
    template_id = str(payload.get("templateId") or "")
    version = str(payload.get("version") or "")
    full_id = ":".join(part for part in [organization_id, template_id, version] if part)
    replacements = {
        "{template_full_id}": full_id,
        "{template_id}": template_id,
        "{template_organization_id}": organization_id,
        "{template_version}": version,
    }
    for marker, value in replacements.items():
        content = content.replace(marker, value)
    return content


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
            "- Upstream source: https://github.com/ds-wizard/science-europe-template.",
            "- This package is intended for DSW document template import.",
        ]
    )
    return "\n".join(lines) + "\n"
