"""Tests for local template staging helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZipFile

from dsw_document_template_tool.tdk import (
    read_local_template_package_coordinates,
    stage_local_template_package,
)


def _write_template_package(
    path: Path,
    *,
    asset: bytes = b"font",
    build_id: str = "first",
    reverse_files: bool = False,
) -> None:
    files = [
        {"content": "one", "fileName": "src/one.j2", "uuid": f"{build_id}-one"},
        {"content": "two", "fileName": "src/two.j2", "uuid": f"{build_id}-two"},
    ]
    if reverse_files:
        files.reverse()
    payload = {
        "id": "dsw:science-europe-zh-hant:1.30.1",
        "organizationId": "dsw",
        "templateId": "science-europe-zh-hant",
        "version": "1.30.1",
        "name": "Science Europe DMP Template (zh-Hant)",
        "createdAt": f"created-{build_id}",
        "updatedAt": f"updated-{build_id}",
        "assets": [
            {
                "contentType": "font/ttf",
                "fileName": "src/fonts/font.ttf",
                "uuid": f"{build_id}-asset",
            }
        ],
        "files": files,
    }
    with ZipFile(path, "w") as archive:
        archive.writestr("template/template.json", json.dumps(payload))
        archive.writestr("template/assets/font.ttf", asset)


def test_stage_local_template_package_uses_content_addressed_coordinates(
    tmp_path: Path,
) -> None:
    """Changed package bytes must never reuse a stale released template in DSW."""

    package_path = tmp_path / "template.zip"
    _write_template_package(package_path)

    first_package, first_coordinates = stage_local_template_package(
        source_package=package_path,
    )
    unchanged_package: Path | None = None
    second_package: Path | None = None
    try:
        assert first_coordinates.organization_id == "dsw"
        assert first_coordinates.version == "1.30.1"
        assert first_coordinates.template_id.startswith("science-europe-zh-hant-local-")
        assert len(first_coordinates.template_id.rsplit("-", 1)[-1]) == 12
        assert read_local_template_package_coordinates(first_package) == first_coordinates
        with ZipFile(first_package) as archive:
            payload = json.loads(archive.read("template/template.json"))
            assert payload["id"] == first_coordinates.full_id
            assert payload["name"] == "Science Europe DMP Template (zh-Hant)"
            assert archive.read("template/assets/font.ttf") == b"font"

        _write_template_package(
            package_path,
            build_id="second",
            reverse_files=True,
        )
        unchanged_package, unchanged_coordinates = stage_local_template_package(
            source_package=package_path,
        )
        assert unchanged_coordinates == first_coordinates

        _write_template_package(package_path, asset=b"changed font")
        second_package, second_coordinates = stage_local_template_package(
            source_package=package_path,
        )
        assert second_coordinates != first_coordinates
    finally:
        shutil.rmtree(first_package.parent, ignore_errors=True)
        if unchanged_package is not None:
            shutil.rmtree(unchanged_package.parent, ignore_errors=True)
        if second_package is not None:
            shutil.rmtree(second_package.parent, ignore_errors=True)
