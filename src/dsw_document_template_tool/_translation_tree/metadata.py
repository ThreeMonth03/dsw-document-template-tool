"""Template metadata patching for synced translated outputs."""

from __future__ import annotations

import json
from pathlib import Path


def patch_template_metadata(
    *,
    output_dir: Path,
    organization_id: str | None,
    template_id: str | None,
    name: str | None,
    version: str | None,
) -> None:
    updates = {
        "organizationId": organization_id,
        "templateId": template_id,
        "name": name,
        "version": version,
    }
    updates = {key: value for key, value in updates.items() if value is not None}
    if not updates:
        return

    template_path = output_dir / "template.json"
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    for key, value in updates.items():
        payload[key] = value
    template_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
