"""Helpers that stage local templates and invoke `dsw-tdk` safely."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
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
    return _coordinates_from_payload(payload, source=template_json_path)


def read_local_template_package_coordinates(package_path: Path) -> TemplateCoordinates:
    """Read document template coordinates from a packaged template ZIP."""

    try:
        with zipfile.ZipFile(package_path) as archive:
            member = _template_json_member(archive)
            payload = json.loads(archive.read(member).decode("utf-8"))
    except (OSError, KeyError, UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        raise TemplateToolError(f"Could not read template package {package_path}: {exc}") from exc
    return _coordinates_from_payload(payload, source=package_path)


def stage_local_template_package(
    *,
    source_package: Path,
) -> tuple[Path, TemplateCoordinates]:
    """Copy a package under content-addressed coordinates for repeatable local renders."""

    source_package = source_package.resolve()
    original_coordinates = read_local_template_package_coordinates(source_package)
    package_digest = hashlib.sha256(source_package.read_bytes()).hexdigest()[:12]
    stage_coordinates = TemplateCoordinates(
        organization_id=original_coordinates.organization_id,
        template_id=f"{original_coordinates.template_id}-local-{package_digest}",
        version=original_coordinates.version,
    )
    temp_root = Path(tempfile.mkdtemp(prefix="dsw-template-package-"))
    staged_package = temp_root / source_package.name
    try:
        with (
            zipfile.ZipFile(source_package) as source_archive,
            zipfile.ZipFile(staged_package, "w") as staged_archive,
        ):
            template_member = _template_json_member(source_archive)
            for member in source_archive.infolist():
                content = source_archive.read(member)
                if member.filename == template_member:
                    payload = json.loads(content.decode("utf-8"))
                    content = (
                        json.dumps(
                            _patched_template_payload(
                                payload=payload,
                                original_coordinates=original_coordinates,
                                stage_coordinates=stage_coordinates,
                                subject_label=None,
                            ),
                            indent=2,
                            ensure_ascii=False,
                        )
                        + "\n"
                    ).encode("utf-8")
                staged_archive.writestr(member, content)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    return staged_package, stage_coordinates


def _coordinates_from_payload(
    payload: object,
    *,
    source: Path,
) -> TemplateCoordinates:
    if not isinstance(payload, dict):
        raise TemplateToolError(f"Expected a JSON object in {source}")
    try:
        coordinates = TemplateCoordinates(
            organization_id=str(payload["organizationId"]),
            template_id=str(payload["templateId"]),
            version=str(payload["version"]),
        )
    except KeyError as exc:
        raise TemplateToolError(f"template.json in {source} is missing {exc.args[0]!r}") from exc
    package_id = payload.get("id")
    if package_id is not None and package_id != coordinates.full_id:
        raise TemplateToolError(
            f"Template ID {package_id!r} in {source} does not match {coordinates.full_id!r}"
        )
    return coordinates


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
    payload = _patched_template_payload(
        payload=payload,
        original_coordinates=original_coordinates,
        stage_coordinates=stage_coordinates,
        subject_label=subject_label,
    )
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


def _patched_template_payload(
    *,
    payload: dict[str, object],
    original_coordinates: TemplateCoordinates,
    stage_coordinates: TemplateCoordinates,
    subject_label: str | None,
) -> dict[str, object]:
    patched = dict(payload)
    if "id" in patched:
        patched["id"] = stage_coordinates.full_id
    patched["organizationId"] = stage_coordinates.organization_id
    patched["templateId"] = stage_coordinates.template_id
    patched["version"] = stage_coordinates.version
    original_name = str(patched.get("name", original_coordinates.template_id))
    if subject_label and subject_label.lower() not in original_name.lower():
        patched["name"] = f"{original_name} [{subject_label}]"
    return patched


def _template_json_member(archive: zipfile.ZipFile) -> str:
    names = archive.namelist()
    if "template.json" in names:
        return "template.json"
    matches = [name for name in names if name.endswith("/template.json")]
    if len(matches) != 1:
        raise TemplateToolError(
            f"Expected exactly one template.json in package, found {len(matches)}"
        )
    return matches[0]


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
