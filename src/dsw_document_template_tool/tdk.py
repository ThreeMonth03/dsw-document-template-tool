"""Helpers that stage local templates and invoke `dsw-tdk` safely."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Protocol

from .models import TemplateCoordinates

_MAX_TEMPLATE_JSON_SIZE = 16 * 1024 * 1024
_MAX_PACKAGE_UNCOMPRESSED_SIZE = 128 * 1024 * 1024
_COPY_BUFFER_SIZE = 1024 * 1024


class _Digest(Protocol):
    def update(self, data: bytes, /) -> None: ...


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
            _validate_package_size(archive)
            member = _template_json_member(archive)
            payload = json.loads(_read_template_json(archive, member).decode("utf-8"))
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
    # Namespace the staging scheme itself: older staged packages could share
    # database-wide file UUIDs and have silently lost files during import.
    package_digest = hashlib.sha256(
        f"staging-v2:{_canonical_template_package_digest(source_package)}".encode()
    ).hexdigest()[:12]
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
            _validate_package_size(source_archive)
            template_member = _template_json_member(source_archive)
            for member in source_archive.infolist():
                if member.filename == template_member:
                    payload = json.loads(
                        _read_template_json(source_archive, member).decode("utf-8")
                    )
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
                elif member.is_dir():
                    staged_archive.writestr(member, b"")
                else:
                    with (
                        source_archive.open(member) as source,
                        staged_archive.open(member, "w") as destination,
                    ):
                        shutil.copyfileobj(source, destination, length=_COPY_BUFFER_SIZE)
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
    for kind in ("files", "assets"):
        items = patched.get(kind)
        if isinstance(items, list):
            patched[kind] = [
                {
                    **item,
                    "uuid": str(
                        uuid.uuid5(
                            uuid.NAMESPACE_URL,
                            f"dsw-stage-v2:{stage_coordinates.full_id}:{kind}:{item['fileName']}",
                        )
                    ),
                }
                if isinstance(item, dict) and isinstance(item.get("fileName"), str)
                else item
                for item in items
            ]
    original_name = str(patched.get("name", original_coordinates.template_id))
    if subject_label and subject_label.lower() not in original_name.lower():
        patched["name"] = f"{original_name} [{subject_label}]"
    return patched


def _template_json_member(archive: zipfile.ZipFile) -> str:
    names = archive.namelist()
    seen_names: set[str] = set()
    duplicate_names: set[str] = set()
    for name in names:
        if name in seen_names:
            duplicate_names.add(name)
        else:
            seen_names.add(name)
    if duplicate_names:
        raise TemplateToolError(
            "Template package contains duplicate ZIP members: " + ", ".join(sorted(duplicate_names))
        )
    if "template.json" in names:
        return "template.json"
    matches = [name for name in names if name.endswith("/template.json")]
    if len(matches) != 1:
        raise TemplateToolError(
            f"Expected exactly one template.json in package, found {len(matches)}"
        )
    return matches[0]


def _canonical_template_package_digest(package_path: Path) -> str:
    """Hash render-relevant package content while ignoring TDK build metadata."""

    digest = hashlib.sha256()
    with zipfile.ZipFile(package_path) as archive:
        _validate_package_size(archive)
        template_member = _template_json_member(archive)
        members = sorted(
            (member for member in archive.infolist() if not member.is_dir()),
            key=lambda member: member.filename,
        )
        for member in members:
            _update_digest(digest, member.filename.encode("utf-8"))
            if member.filename == template_member:
                payload = json.loads(_read_template_json(archive, member).decode("utf-8"))
                content = _canonical_template_payload_bytes(payload)
                _update_digest(digest, content)
            else:
                digest.update(member.file_size.to_bytes(8, byteorder="big"))
                with archive.open(member) as source:
                    while chunk := source.read(_COPY_BUFFER_SIZE):
                        digest.update(chunk)
    return digest.hexdigest()


def _validate_package_size(archive: zipfile.ZipFile) -> None:
    """Reject packages whose declared expansion would consume excessive resources."""

    total_size = sum(member.file_size for member in archive.infolist())
    if total_size > _MAX_PACKAGE_UNCOMPRESSED_SIZE:
        raise TemplateToolError(
            "Template package expands to "
            f"{total_size} bytes; limit is {_MAX_PACKAGE_UNCOMPRESSED_SIZE} bytes"
        )


def _read_template_json(
    archive: zipfile.ZipFile,
    member: str | zipfile.ZipInfo,
) -> bytes:
    info = archive.getinfo(member) if isinstance(member, str) else member
    if info.file_size > _MAX_TEMPLATE_JSON_SIZE:
        raise TemplateToolError(
            f"template.json is {info.file_size} bytes; limit is {_MAX_TEMPLATE_JSON_SIZE} bytes"
        )
    with archive.open(info) as source:
        content = source.read(_MAX_TEMPLATE_JSON_SIZE + 1)
    if len(content) > _MAX_TEMPLATE_JSON_SIZE:
        raise TemplateToolError(f"template.json exceeds the {_MAX_TEMPLATE_JSON_SIZE}-byte limit")
    return content


def _canonical_template_payload_bytes(payload: object) -> bytes:
    if not isinstance(payload, dict):
        raise TemplateToolError("Expected template.json to contain a JSON object")
    canonical = dict(payload)
    canonical.pop("createdAt", None)
    canonical.pop("updatedAt", None)
    for key in ("assets", "files"):
        items = canonical.get(key)
        if not isinstance(items, list):
            continue
        normalized_items: list[object] = []
        for item in items:
            if isinstance(item, dict):
                normalized_item = dict(item)
                normalized_item.pop("uuid", None)
                normalized_items.append(normalized_item)
            else:
                normalized_items.append(item)
        canonical[key] = sorted(
            normalized_items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )
    return json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _update_digest(digest: _Digest, content: bytes) -> None:
    digest.update(len(content).to_bytes(8, byteorder="big"))
    digest.update(content)


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
