"""Tests for API-side reference parsing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dsw_document_template_tool.api import (
    DSWApiClient,
    _apply_download_host_alias,
    _read_knowledge_model_package_id_from_bundle,
)


class FakeRequest:
    """Minimal request metadata used by API error formatting."""

    def __init__(self, method: str, url: str) -> None:
        self.method = method
        self.url = url


class FakeResponse:
    """Small response object for API unit tests without network calls."""

    def __init__(self, status_code: int, payload: Any, *, method: str, url: str) -> None:
        self.status_code = status_code
        self._payload = payload
        self.request = FakeRequest(method, url)
        self.text = str(payload)

    def json(self) -> Any:
        return self._payload


class LegacyPackageListingClient(DSWApiClient):
    """Client whose DSW server does not expose filtered KM package listing."""

    def __init__(self) -> None:
        super().__init__(api_url="http://localhost:3000/wizard-api")
        self.uploaded_bundles: list[Path] = []

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        return FakeResponse(
            404,
            {"message": "Not Found", "status": 404},
            method=method,
            url=f"{self.api_url}{endpoint}",
        )

    def upload_knowledge_model_package_bundle(self, bundle_path: Path) -> dict[str, Any]:
        self.uploaded_bundles.append(bundle_path)
        return {"uuid": "11111111-1111-4111-8111-111111111111"}


def test_read_knowledge_model_package_id_from_bundle_prefers_id(tmp_path: Path) -> None:
    """A local `.km` bundle should expose its package coordinates."""

    bundle_path = tmp_path / "root-zh-hant-2.7.0.km"
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


def test_find_knowledge_model_package_uuid_returns_none_for_legacy_404() -> None:
    """Older DSW servers may not support the filtered KM package listing endpoint."""

    client = LegacyPackageListingClient()

    assert client.find_knowledge_model_package_uuid_by_id("dsw:root-zh-hant:2.7.0") is None


def test_local_knowledge_model_bundle_uploads_when_legacy_listing_is_missing(
    tmp_path: Path,
) -> None:
    """Local KM bundles should still render previews on older DSW API versions."""

    bundle_path = tmp_path / "root-zh-hant-2.7.0.km"
    bundle_path.write_text(
        """
{
  "id": "dsw:root-zh-hant:2.7.0"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    client = LegacyPackageListingClient()

    resolved_uuid = client.resolve_knowledge_model_package_uuid(str(bundle_path))

    assert resolved_uuid == "11111111-1111-4111-8111-111111111111"
    assert client.uploaded_bundles == [bundle_path]
