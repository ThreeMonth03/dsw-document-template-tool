"""Tests for API-side reference parsing helpers."""

from __future__ import annotations

from pathlib import Path

from dsw_document_template_tool.api import (
    _apply_download_host_alias,
    _read_knowledge_model_package_id_from_bundle,
)


def test_read_knowledge_model_package_id_from_bundle_prefers_id(tmp_path: Path) -> None:
    """A local `.km` bundle should expose its package coordinates."""

    bundle_path = tmp_path / "final_translated.km"
    bundle_path.write_text(
        """
{
  "id": "dsw:root-zh-hant:2.7.0",
  "organizationId": "ignored",
  "kmId": "ignored",
  "version": "0.0.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert _read_knowledge_model_package_id_from_bundle(bundle_path) == "dsw:root-zh-hant:2.7.0"


def test_read_knowledge_model_package_id_from_bundle_returns_none_for_non_json(
    tmp_path: Path,
) -> None:
    """Non-bundle files should not be treated as package references."""

    bundle_path = tmp_path / "not-a-bundle.km"
    bundle_path.write_text("hello\n", encoding="utf-8")

    assert _read_knowledge_model_package_id_from_bundle(bundle_path) is None


def test_apply_download_host_alias_preserves_original_host_header(monkeypatch) -> None:
    """Presigned S3 URLs can connect through localhost without breaking Host."""

    monkeypatch.setenv("DSW_DOWNLOAD_HOST_ALIAS", "host.docker.internal=localhost")

    url, headers = _apply_download_host_alias(
        "http://host.docker.internal:9100/engine-wizard/documents/file.html?signature=abc"
    )

    assert url == "http://localhost:9100/engine-wizard/documents/file.html?signature=abc"
    assert headers == {"Host": "host.docker.internal:9100"}
