"""Tests for API-side reference parsing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from dsw_document_template_tool.api import (
    DSWApiClient,
    DSWAPIError,
    KnowledgeModelPackageReference,
    _apply_download_host_alias,
    _read_document_template_id_from_bundle,
    _read_knowledge_model_package_id_from_bundle,
)
from dsw_document_template_tool.models import DocumentTemplateReference


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


def _package_payload(
    *,
    uuid: str | None = None,
    version: str = "2.7.0",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pId": f"dsw:root-zh-hant:{version}",
        "organizationId": "dsw",
        "kmId": "root-zh-hant",
        "version": version,
    }
    if uuid is not None:
        payload["uuid"] = uuid
    return payload


class MissingPackageListingClient(DSWApiClient):
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

    def upload_knowledge_model_package_bundle_reference(
        self, bundle_path: Path
    ) -> KnowledgeModelPackageReference:
        self.uploaded_bundles.append(bundle_path)
        return KnowledgeModelPackageReference(uuid="11111111-1111-4111-8111-111111111111")


class BundleUploadClient(DSWApiClient):
    """Client that records bundle upload attempts."""

    def __init__(self) -> None:
        super().__init__(api_url="http://localhost:3000/wizard-api")
        self.bundle_endpoints: list[str] = []

    def _post_bundle(self, endpoint: str, bundle_path: Path) -> FakeResponse:
        self.bundle_endpoints.append(endpoint)
        return FakeResponse(
            201,
            [_package_payload(version="1.0.0"), _package_payload()],
            method="POST",
            url=f"{self.api_url}{endpoint}",
        )


class MismatchedBundleUploadClient(BundleUploadClient):
    """Client whose bundle upload omits the requested package version."""

    def _post_bundle(self, endpoint: str, bundle_path: Path) -> FakeResponse:
        self.bundle_endpoints.append(endpoint)
        return FakeResponse(
            201,
            [_package_payload(version="1.0.0")],
            method="POST",
            url=f"{self.api_url}{endpoint}",
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        return FakeResponse(
            200,
            [],
            method=method,
            url=f"{self.api_url}{endpoint}",
        )


class DocumentTemplateBundleUploadClient(DSWApiClient):
    """Client that records document template package upload attempts."""

    def __init__(self) -> None:
        super().__init__(api_url="http://localhost:3000/wizard-api")
        self.bundle_uploads: list[tuple[str, Path, str]] = []

    def _post_bundle(
        self,
        endpoint: str,
        bundle_path: Path,
        *,
        content_type: str = "application/json",
    ) -> FakeResponse:
        self.bundle_uploads.append((endpoint, bundle_path, content_type))
        return FakeResponse(
            201,
            {
                "name": "Science Europe DMP Template (zh-Hant)",
                "uuid": "33333333-3333-4333-8333-333333333333",
            },
            method="POST",
            url=f"{self.api_url}{endpoint}",
        )


class LegacyDocumentTemplateBundleUploadClient(DocumentTemplateBundleUploadClient):
    """Client returning the ID-based DSW 4.26 document-template shape."""

    def _post_bundle(
        self,
        endpoint: str,
        bundle_path: Path,
        *,
        content_type: str = "application/json",
    ) -> FakeResponse:
        self.bundle_uploads.append((endpoint, bundle_path, content_type))
        return FakeResponse(
            201,
            {
                "id": "dsw:science-europe-zh-hant:1.29.1",
                "name": "Science Europe DMP Template (zh-Hant)",
            },
            method="POST",
            url=f"{self.api_url}{endpoint}",
        )


class DuplicateDocumentTemplateUploadClient(DSWApiClient):
    """Client with an already-imported document template package."""

    def __init__(self, error_code: str = "error.validation.tml_id_uniqueness") -> None:
        super().__init__(api_url="http://localhost:3000/wizard-api")
        self.bundle_uploads: list[tuple[str, Path, str]] = []
        self.error_code = error_code

    def _post_bundle(
        self,
        endpoint: str,
        bundle_path: Path,
        *,
        content_type: str = "application/json",
    ) -> FakeResponse:
        self.bundle_uploads.append((endpoint, bundle_path, content_type))
        return FakeResponse(
            400,
            {
                "error": {
                    "code": self.error_code,
                    "params": ["dsw:science-europe-zh-hant:1.30.1"],
                },
                "status": 400,
            },
            method="POST",
            url=f"{self.api_url}{endpoint}",
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        return FakeResponse(
            200,
            [
                {
                    "uuid": "44444444-4444-4444-8444-444444444444",
                    "organizationId": "dsw",
                    "templateId": "science-europe-zh-hant",
                    "version": "1.30.1",
                }
            ],
            method=method,
            url=f"{self.api_url}{endpoint}",
        )


class ProjectCreateFallbackClient(DSWApiClient):
    """Client that records project create fallback attempts."""

    def __init__(self, package_ref: KnowledgeModelPackageReference) -> None:
        super().__init__(api_url="http://localhost:3000/wizard-api")
        self.package_ref = package_ref
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def resolve_knowledge_model_package_reference(
        self, package_id: str
    ) -> KnowledgeModelPackageReference:
        return self.package_ref

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        self.requests.append((method, endpoint, json))
        if endpoint == "/projects" and json and "knowledgeModelPackageId" in json:
            return FakeResponse(
                201,
                {"uuid": "22222222-2222-4222-8222-222222222222"},
                method=method,
                url=f"{self.api_url}{endpoint}",
            )
        return FakeResponse(
            404,
            {"message": "Not Found"},
            method=method,
            url=f"{self.api_url}{endpoint}",
        )


class DocumentCreateClient(DSWApiClient):
    """Client that records released document creation payloads."""

    def __init__(self) -> None:
        super().__init__(api_url="http://localhost:3000/wizard-api")
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        self.requests.append((method, endpoint, json))
        return FakeResponse(
            201,
            {"uuid": "55555555-5555-4555-8555-555555555555"},
            method=method,
            url=f"{self.api_url}{endpoint}",
        )


class PreviewSettingsClient(DSWApiClient):
    """Client that records preview settings body payloads."""

    def __init__(self) -> None:
        super().__init__(api_url="http://localhost:3000/wizard-api")
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> FakeResponse:
        self.requests.append((method, endpoint, json))
        return FakeResponse(
            200,
            {"ok": True},
            method=method,
            url=f"{self.api_url}{endpoint}",
        )


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


def test_find_draft_reference_accepts_id_field_from_older_dsw() -> None:
    """DSW 4.26 draft lists expose `id`, not `uuid`."""

    class OlderDraftClient(DSWApiClient):
        def _request(
            self,
            method: str,
            endpoint: str,
            *,
            params: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
        ) -> FakeResponse:
            return FakeResponse(
                200,
                {
                    "_embedded": {
                        "documentTemplateDrafts": [
                            {
                                "id": "myorg:science-europe-zh-hant:1.29.1",
                                "organizationId": "myorg",
                                "templateId": "science-europe-zh-hant",
                                "version": "1.29.1",
                            }
                        ]
                    }
                },
                method=method,
                url=f"{self.api_url}{endpoint}",
            )

    client = OlderDraftClient(api_url="http://localhost:3000/wizard-api")

    assert (
        client.find_draft_uuid_by_id("dsw:science-europe-zh-hant:1.29.1")
        == "myorg:science-europe-zh-hant:1.29.1"
    )


def test_find_knowledge_model_package_uuid_returns_none_when_listing_is_missing() -> None:
    """Missing KM package listing endpoint should be reported as unresolved."""

    client = MissingPackageListingClient()

    assert client.find_knowledge_model_package_uuid_by_id("dsw:root-zh-hant:2.7.0") is None


def test_local_knowledge_model_bundle_uploads_when_listing_is_missing(
    tmp_path: Path,
) -> None:
    """Local KM bundles should upload when package coordinates are not listed."""

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
    client = MissingPackageListingClient()

    resolved_uuid = client.resolve_knowledge_model_package_uuid(str(bundle_path))

    assert resolved_uuid == "11111111-1111-4111-8111-111111111111"
    assert client.uploaded_bundles == [bundle_path]


def test_bundle_upload_accepts_list_payload(tmp_path: Path) -> None:
    """DSW 4.26 history lists should resolve the exact requested package."""

    bundle_path = tmp_path / "root-zh-hant-2.7.0.km"
    bundle_path.write_text('{"id": "dsw:root-zh-hant:2.7.0"}\n', encoding="utf-8")
    client = BundleUploadClient()

    package_ref = client.upload_knowledge_model_package_bundle_reference(bundle_path)

    assert client.bundle_endpoints == ["/knowledge-model-packages/bundle"]
    assert package_ref.package_id == "dsw:root-zh-hant:2.7.0"
    assert package_ref.uuid is None


def test_bundle_upload_rejects_history_without_requested_package(tmp_path: Path) -> None:
    """A partial history import must not silently select an older KM package."""

    bundle_path = tmp_path / "root-zh-hant-2.7.0.km"
    bundle_path.write_text('{"id": "dsw:root-zh-hant:2.7.0"}\n', encoding="utf-8")
    client = MismatchedBundleUploadClient()

    with pytest.raises(DSWAPIError, match="dsw:root-zh-hant:2.7.0"):
        client.upload_knowledge_model_package_bundle_reference(bundle_path)


def test_document_template_package_upload_uses_bundle_endpoint(tmp_path: Path) -> None:
    """Released document template packages should upload through the package endpoint."""

    bundle_path = tmp_path / "template.zip"
    bundle_path.write_bytes(b"zip")
    client = DocumentTemplateBundleUploadClient()

    reference = client.upload_document_template_bundle_reference(bundle_path)

    assert reference.uuid == "33333333-3333-4333-8333-333333333333"
    assert client.bundle_uploads == [("/document-templates/bundle", bundle_path, "application/zip")]


def test_legacy_document_template_upload_uses_template_id(tmp_path: Path) -> None:
    """DSW 4.26 package imports should preserve the returned template ID."""

    bundle_path = tmp_path / "template.zip"
    with ZipFile(bundle_path, "w") as archive:
        archive.writestr(
            "template/template.json",
            '{"id": "dsw:science-europe-zh-hant:1.29.1"}\n',
        )
    client = LegacyDocumentTemplateBundleUploadClient()

    reference = client.upload_document_template_bundle_reference(bundle_path)

    assert reference == DocumentTemplateReference(template_id="dsw:science-europe-zh-hant:1.29.1")


def test_read_document_template_id_from_package_zip(tmp_path: Path) -> None:
    """Packaged document templates keep their coordinates in template.json."""

    bundle_path = tmp_path / "template.zip"
    with ZipFile(bundle_path, "w") as archive:
        archive.writestr(
            "template/template.json",
            '{"id": "dsw:science-europe-zh-hant:1.30.1"}\n',
        )

    assert _read_document_template_id_from_bundle(bundle_path) == (
        "dsw:science-europe-zh-hant:1.30.1"
    )


@pytest.mark.parametrize(
    "error_code",
    [
        "error.database.unique_constraint_violation",
        "error.validation.tml_id_uniqueness",
    ],
)
def test_duplicate_document_template_package_upload_reuses_existing_template(
    tmp_path: Path,
    error_code: str,
) -> None:
    """Repeated local release checks should render with the existing template."""

    bundle_path = tmp_path / "template.zip"
    with ZipFile(bundle_path, "w") as archive:
        archive.writestr(
            "template/template.json",
            '{"id": "dsw:science-europe-zh-hant:1.30.1"}\n',
        )
    client = DuplicateDocumentTemplateUploadClient(error_code)

    reference = client.upload_document_template_bundle_reference(bundle_path)

    assert reference == DocumentTemplateReference(
        template_id="dsw:science-europe-zh-hant:1.30.1",
        uuid="44444444-4444-4444-8444-444444444444",
    )


@pytest.mark.parametrize(
    ("reference", "expected_field", "expected_value"),
    [
        (
            DocumentTemplateReference(uuid="44444444-4444-4444-8444-444444444444"),
            "documentTemplateUuid",
            "44444444-4444-4444-8444-444444444444",
        ),
        (
            DocumentTemplateReference(template_id="dsw:science-europe-zh-hant:1.29.1"),
            "documentTemplateId",
            "dsw:science-europe-zh-hant:1.29.1",
        ),
    ],
)
def test_document_create_uses_server_template_identifier(
    reference: DocumentTemplateReference,
    expected_field: str,
    expected_value: str,
) -> None:
    """Document creation should follow the identifier exposed by the server."""

    client = DocumentCreateClient()

    client.create_document(
        name="Preview",
        project_uuid="11111111-1111-4111-8111-111111111111",
        document_template=reference,
        format_uuid="22222222-2222-4222-8222-222222222222",
        project_event_uuid=None,
    )

    body = client.requests[0][2]
    assert body is not None
    assert body[expected_field] == expected_value
    other_field = (
        "documentTemplateId" if expected_field == "documentTemplateUuid" else "documentTemplateUuid"
    )
    assert other_field not in body


def test_project_create_falls_back_to_package_id_field() -> None:
    """DSW 4.26/4.29 project creation still uses `knowledgeModelPackageId`."""

    client = ProjectCreateFallbackClient(
        KnowledgeModelPackageReference(package_id="dsw:root-zh-hant:2.7.0")
    )

    created = client.create_project_from_package(
        name="Preview",
        knowledge_model_package_id="ignored",
        question_tag_uuids=[],
        visibility="PrivateProjectVisibility",
        sharing="RestrictedProjectSharing",
    )

    assert created["uuid"] == "22222222-2222-4222-8222-222222222222"
    assert client.requests[0][1] == "/projects"
    assert client.requests[0][2] == {
        "name": "Preview",
        "knowledgeModelPackageId": "dsw:root-zh-hant:2.7.0",
        "visibility": "PrivateProjectVisibility",
        "sharing": "RestrictedProjectSharing",
        "questionTagUuids": [],
    }
