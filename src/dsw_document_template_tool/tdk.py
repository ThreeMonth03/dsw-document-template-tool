"""Helpers that stage local templates and invoke `dsw-tdk` safely."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import TemplateCoordinates


class TemplateToolError(RuntimeError):
    """Raised when a local template cannot be staged or uploaded."""


def read_local_template_coordinates(template_dir: Path) -> TemplateCoordinates:
    """Read document template coordinates from `template.json`."""

    template_json_path = template_dir / "template.json"
    if not template_json_path.is_file():
        raise TemplateToolError(f"Missing template.json in {template_dir}")
    payload = json.loads(template_json_path.read_text(encoding="utf-8"))
    try:
        return TemplateCoordinates(
            organization_id=str(payload["organizationId"]),
            template_id=str(payload["templateId"]),
            version=str(payload["version"]),
        )
    except KeyError as exc:
        raise TemplateToolError(
            f"template.json in {template_dir} is missing {exc.args[0]!r}"
        ) from exc


def stage_local_template_dir(
    *,
    source_dir: Path,
    subject_label: str,
    stage_id: str | None,
) -> tuple[Path, TemplateCoordinates]:
    """Copy a local template to a temporary staging directory and rewrite IDs."""

    original_coordinates = read_local_template_coordinates(source_dir)
    if stage_id is None:
        stage_coordinates = TemplateCoordinates(
            organization_id=original_coordinates.organization_id,
            template_id=f"{original_coordinates.template_id}-{_sanitize_id(subject_label)}",
            version=original_coordinates.version,
        )
    else:
        stage_coordinates = parse_template_coordinates(stage_id)

    temp_root = Path(tempfile.mkdtemp(prefix=f"dsw-template-{_sanitize_id(subject_label)}-"))
    staged_dir = temp_root / source_dir.name
    shutil.copytree(source_dir, staged_dir)
    _patch_template_json(
        staged_dir=staged_dir,
        original_coordinates=original_coordinates,
        stage_coordinates=stage_coordinates,
        subject_label=subject_label,
    )
    return staged_dir, stage_coordinates


def verify_template_dir(*, executable: str, template_dir: Path) -> None:
    """Run `dsw-tdk verify` for one local template directory."""

    _run_subprocess([executable, "verify", str(template_dir)])


def put_template_dir(
    *,
    executable: str,
    template_dir: Path,
    api_url: str,
    api_key: str,
) -> None:
    """Run `dsw-tdk put` for one local template directory."""

    _run_subprocess(
        [
            executable,
            "put",
            str(template_dir),
            "--api-url",
            api_url,
            "--api-key",
            api_key,
        ]
    )


def parse_template_coordinates(value: str) -> TemplateCoordinates:
    """Parse `organizationId:templateId:version` into structured coordinates."""

    parts = value.split(":")
    if len(parts) != 3 or not all(parts):
        raise TemplateToolError(
            f"Expected template coordinates in `org:template:version` format, got {value!r}"
        )
    return TemplateCoordinates(
        organization_id=parts[0],
        template_id=parts[1],
        version=parts[2],
    )


def _patch_template_json(
    *,
    staged_dir: Path,
    original_coordinates: TemplateCoordinates,
    stage_coordinates: TemplateCoordinates,
    subject_label: str,
) -> None:
    template_json_path = staged_dir / "template.json"
    payload = json.loads(template_json_path.read_text(encoding="utf-8"))
    payload["organizationId"] = stage_coordinates.organization_id
    payload["templateId"] = stage_coordinates.template_id
    payload["version"] = stage_coordinates.version
    original_name = str(payload.get("name", stage_coordinates.template_id))
    if subject_label.lower() not in original_name.lower():
        payload["name"] = f"{original_name} [{subject_label}]"
    template_json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    readme_path = staged_dir / "README.md"
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        readme_text = readme_text.replace(
            original_coordinates.full_id,
            stage_coordinates.full_id,
        )
        readme_path.write_text(readme_text, encoding="utf-8")


def _run_subprocess(args: list[str]) -> None:
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError as exc:
        raise TemplateToolError(
            f"Could not find executable {args[0]!r}. Install dependencies or set `tdk.executable`."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise TemplateToolError(
            f"Command failed with exit code {exc.returncode}: {' '.join(args)}"
        ) from exc


def _sanitize_id(value: str) -> str:
    parts = []
    for char in value.lower():
        if char.isalnum():
            parts.append(char)
        elif parts and parts[-1] != "-":
            parts.append("-")
    sanitized = "".join(parts).strip("-")
    return sanitized or "staged"
