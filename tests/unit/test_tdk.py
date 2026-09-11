"""Tests for local template staging helpers."""

from __future__ import annotations

import json
import shutil
import warnings
from pathlib import Path
from zipfile import ZipFile

import pytest

from dsw_document_template_tool import tdk
from dsw_document_template_tool.tdk import (
    TemplateToolError,
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


def test_stage_local_template_package_rejects_excessive_expansion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A package with excessive expansion must be rejected before inflation."""

    package_path = tmp_path / "bomb.zip"
    _write_template_package(package_path, asset=b"0" * 2048)
    monkeypatch.setattr(tdk, "_MAX_PACKAGE_UNCOMPRESSED_SIZE", 1024)

    try:
        stage_local_template_package(source_package=package_path)
    except TemplateToolError as exc:
        assert "expands to" in str(exc)
    else:
        raise AssertionError("oversized package was accepted")


def test_stage_local_template_package_streams_ordinary_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging must not call ZipFile.read, which buffers a whole member."""

    package_path = tmp_path / "template.zip"
    _write_template_package(package_path, asset=b"asset" * 1000)

    def fail_read(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("ZipFile.read buffered an archive member")

    monkeypatch.setattr(ZipFile, "read", fail_read)
    staged_package, _ = stage_local_template_package(source_package=package_path)
    try:
        with ZipFile(staged_package) as archive:
            with archive.open("template/assets/font.ttf") as asset:
                assert asset.read() == b"asset" * 1000
    finally:
        shutil.rmtree(staged_package.parent, ignore_errors=True)


def test_stage_local_template_package_rejects_duplicate_members(tmp_path: Path) -> None:
    """Ambiguous ZIP members must not share a staged content-addressed ID."""

    package_path = tmp_path / "template.zip"
    _write_template_package(package_path)
    with ZipFile(package_path, "a") as archive, warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        archive.writestr("template/assets/font.ttf", b"ambiguous font")

    with pytest.raises(
        TemplateToolError,
        match=r"duplicate ZIP members: template/assets/font\.ttf",
    ):
        stage_local_template_package(source_package=package_path)


def test_staged_package_file_ids_are_isolated_even_with_stable_source_ids(tmp_path: Path) -> None:
    """DSW file UUIDs must not collide with the source or another staged version."""
    package = tmp_path / "template.zip"
    staged = []
    try:
        results = []
        for asset in (b"font", b"different font", b"font"):
            _write_template_package(package, asset=asset, build_id="stable")
            with ZipFile(package) as archive:
                source = json.loads(archive.read("template/template.json"))
            output, _ = stage_local_template_package(source_package=package)
            staged.append(output)
            with ZipFile(output) as archive:
                target = json.loads(archive.read("template/template.json"))
            ids = {item["uuid"] for kind in ("files", "assets") for item in target[kind]}
            source_ids = {item["uuid"] for kind in ("files", "assets") for item in source[kind]}
            assert ids.isdisjoint(source_ids)
            results.append(ids)
        assert results[0].isdisjoint(results[1])
        assert results[0] == results[2]
    finally:
        for output in staged:
            shutil.rmtree(output.parent, ignore_errors=True)
