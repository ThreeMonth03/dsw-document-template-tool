"""Small DSW API client for headless preview/document regression flows."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests


class DSWAPIError(RuntimeError):
    """Raised when the DSW API returns an unexpected response."""


class DSWApiClient:
    """Minimal API client used by the regression workflow."""

    def __init__(self, *, api_url: str, verify_ssl: bool = False):
        self.api_url = api_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.token: str | None = None

    def close(self) -> None:
        """Close the underlying requests session."""

        self.session.close()

    def set_token(self, token: str) -> None:
        """Store the bearer token for future authenticated requests."""

        self.token = token

    def login(self, *, email: str, password: str) -> str:
        """Create an API token using DSW email/password credentials."""

        response = self.session.post(
            f"{self.api_url}/tokens",
            json={"email": email, "password": password, "code": None},
            verify=self.verify_ssl,
            timeout=30,
        )
        self._raise_for_status(response, expected_statuses={200, 201})
        payload = response.json()
        token = payload.get("token")
        if not isinstance(token, str) or not token:
            raise DSWAPIError("DSW did not return a valid bearer token")
        self.token = token
        return token

    def get_current_user(self) -> dict[str, Any]:
        """Fetch the current authenticated user."""

        return self._request_json("GET", "/users/current")

    def find_draft_uuid_by_id(self, template_id: str) -> str | None:
        """Resolve draft coordinates like `org:id:version` into a draft UUID."""

        if template_id.count(":") != 2:
            return None
        organization_id, short_template_id, version = template_id.split(":")
        payload = self._request_json(
            "GET",
            "/document-template-drafts",
            params={"size": 10000, "page": 0, "q": short_template_id},
        )
        drafts = payload.get("_embedded", {}).get("documentTemplateDrafts", [])
        partial_match = None
        for draft in drafts:
            if not isinstance(draft, dict):
                continue
            uuid = draft.get("uuid")
            if not isinstance(uuid, str):
                continue
            if (
                draft.get("organizationId") == organization_id
                and draft.get("templateId") == short_template_id
                and draft.get("version") == version
            ):
                return uuid
            if draft.get("templateId") == short_template_id and draft.get("version") == version:
                partial_match = uuid
        return partial_match

    def check_draft_exists(self, draft_uuid: str) -> bool:
        """Return whether a specific draft UUID exists."""

        response = self._request("GET", f"/document-template-drafts/{draft_uuid}")
        if response.status_code == 404:
            return False
        self._raise_for_status(response)
        return True

    def resolve_document_template_uuid(self, template_id: str) -> str:
        """Resolve released template coordinates into the API's UUID field."""

        if _looks_like_uuid(template_id):
            return template_id
        if template_id.count(":") != 2:
            raise DSWAPIError(
                "Released template references must be a UUID or `org:template:version`, "
                f"got {template_id!r}"
            )
        organization_id, short_template_id, version = template_id.split(":")
        payload = self._request_payload(
            "GET",
            "/document-templates/all",
            params={
                "organizationId": organization_id,
                "templateId": short_template_id,
            },
        )
        items = payload if isinstance(payload, list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            if (
                item.get("organizationId") == organization_id
                and item.get("templateId") == short_template_id
                and item.get("version") == version
            ):
                resolved_uuid = item.get("uuid")
                if isinstance(resolved_uuid, str) and resolved_uuid:
                    return resolved_uuid
        raise DSWAPIError(f"Could not resolve released template UUID for {template_id!r}")

    def resolve_knowledge_model_package_uuid(self, package_id: str) -> str:
        """Resolve released KM package coordinates into the API's UUID field."""

        if _looks_like_uuid(package_id):
            return package_id
        bundle_path = Path(package_id).expanduser()
        if bundle_path.is_file():
            return self._resolve_knowledge_model_package_bundle(bundle_path)
        if package_id.count(":") != 2:
            raise DSWAPIError(
                "Knowledge model package references must be a UUID, `org:km:version`, "
                "or a local `.km` bundle path, "
                f"got {package_id!r}"
            )
        resolved_uuid = self.find_knowledge_model_package_uuid_by_id(package_id)
        if resolved_uuid is not None:
            return resolved_uuid
        raise DSWAPIError(f"Could not resolve KM package UUID for {package_id!r}")

    def find_knowledge_model_package_uuid_by_id(self, package_id: str) -> str | None:
        """Resolve KM coordinates like `org:km:version` into a package UUID."""

        organization_id, km_id, version = package_id.split(":")
        payload = self._request_json(
            "GET",
            "/knowledge-model-packages",
            params={
                "organizationId": organization_id,
                "kmId": km_id,
                "page": 0,
                "size": 1000,
            },
        )
        items = payload.get("_embedded", {}).get("knowledgeModelPackages", [])
        for item in items:
            if not isinstance(item, dict):
                continue
            if (
                item.get("organizationId") == organization_id
                and item.get("kmId") == km_id
                and item.get("version") == version
            ):
                resolved_uuid = item.get("uuid")
                if isinstance(resolved_uuid, str) and resolved_uuid:
                    return resolved_uuid
        return None

    def create_project_from_package(
        self,
        *,
        name: str,
        knowledge_model_package_id: str,
        question_tag_uuids: list[str],
        visibility: str,
        sharing: str,
    ) -> dict[str, Any]:
        """Create one fixture project."""

        knowledge_model_package_uuid = self.resolve_knowledge_model_package_uuid(
            knowledge_model_package_id
        )
        body = {
            "name": name,
            "knowledgeModelPackageUuid": knowledge_model_package_uuid,
            "visibility": visibility,
            "sharing": sharing,
            "questionTagUuids": question_tag_uuids,
        }
        return self._request_json("POST", "/projects", json=body, expected_status=201)

    def put_project_content(self, *, project_uuid: str, events: list[dict[str, Any]]) -> None:
        """Apply a stable fixture event list to one project."""

        response = self._request(
            "PUT",
            f"/projects/{project_uuid}/content",
            json={"events": events},
        )
        self._raise_for_status(response, expected_statuses={200, 204})

    def get_latest_project_event_uuid(self, project_uuid: str) -> str:
        """Return the newest event UUID for one project."""

        payload = self._request_json(
            "GET",
            f"/projects/{project_uuid}/events",
            params={"size": 1, "sort": "createdAt,desc", "page": 0},
        )
        events = payload.get("_embedded", {}).get("projectEvents", [])
        if not events:
            raise DSWAPIError(f"No project events were found for project {project_uuid}")
        latest = events[0]
        if not isinstance(latest, dict):
            raise DSWAPIError(f"Unexpected project event payload for project {project_uuid}")
        event_uuid = latest.get("uuid")
        if not isinstance(event_uuid, str) or not event_uuid:
            raise DSWAPIError(f"Latest project event for {project_uuid} did not include a UUID")
        return event_uuid

    def delete_project(self, project_uuid: str) -> None:
        """Delete a fixture project."""

        response = self._request("DELETE", f"/projects/{project_uuid}")
        self._raise_for_status(response, expected_statuses={204})

    def upload_knowledge_model_package_bundle(self, bundle_path: Path) -> dict[str, Any]:
        """Upload one local KM bundle to the DSW API."""

        url = f"{self.api_url}/knowledge-model-packages/bundle"
        headers = {"User-Agent": "dsw-document-template-tool"}
        if self.token is not None:
            headers["Authorization"] = f"Bearer {self.token}"
        with bundle_path.open("rb") as bundle_file:
            response = self.session.post(
                url=url,
                headers=headers,
                files={"file": (bundle_path.name, bundle_file, "application/json")},
                verify=self.verify_ssl,
                timeout=120,
            )
        self._raise_for_status(response, expected_statuses={200})
        payload = response.json()
        if not isinstance(payload, dict):
            raise DSWAPIError("KM bundle upload did not return a JSON object")
        return payload

    def put_draft_preview_settings(
        self,
        *,
        draft_uuid: str,
        format_uuid: str,
        project_uuid: str,
    ) -> dict[str, Any]:
        """Bind one draft preview to a format and a project."""

        body = {
            "formatUuid": format_uuid,
            "projectUuid": project_uuid,
            "knowledgeModelEditorUuid": None,
        }
        return self._request_json(
            "PUT",
            f"/document-template-drafts/{draft_uuid}/documents/preview/settings",
            json=body,
            expected_status=200,
        )

    def poll_draft_preview_url(
        self,
        *,
        draft_uuid: str,
        timeout_seconds: int,
        poll_seconds: float,
    ) -> str:
        """Poll the preview endpoint until a downloadable URL is ready."""

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            response = self._request(
                "GET",
                f"/document-template-drafts/{draft_uuid}/documents/preview",
            )
            if response.status_code == 202:
                time.sleep(poll_seconds)
                continue
            self._raise_for_status(response, expected_statuses={200})
            payload = response.json()
            url = payload.get("url")
            if isinstance(url, str) and url:
                return url
            raise DSWAPIError("Preview finished but no download URL was returned")
        raise DSWAPIError("Timed out while waiting for draft preview generation")

    def create_document(
        self,
        *,
        name: str,
        project_uuid: str,
        document_template_uuid: str,
        format_uuid: str,
        project_event_uuid: str | None,
    ) -> dict[str, Any]:
        """Queue one final document generation job."""

        body = {
            "name": name,
            "projectUuid": project_uuid,
            "documentTemplateUuid": document_template_uuid,
            "formatUuid": format_uuid,
        }
        if project_event_uuid is not None:
            body["projectEventUuid"] = project_event_uuid
        return self._request_json("POST", "/documents", json=body, expected_status=201)

    def list_project_documents(self, project_uuid: str) -> list[dict[str, Any]]:
        """List current documents for one project."""

        payload = self._request_json(
            "GET",
            f"/projects/{project_uuid}/documents",
            params={"size": 1000, "page": 0},
        )
        return payload.get("_embedded", {}).get("documents", [])

    def poll_document_ready(
        self,
        *,
        project_uuid: str,
        document_uuid: str,
        timeout_seconds: int,
        poll_seconds: float,
    ) -> dict[str, Any]:
        """Poll a queued document until it becomes `DoneDocumentState` or errors."""

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            for document in self.list_project_documents(project_uuid):
                if document.get("uuid") != document_uuid:
                    continue
                state = document.get("state")
                if state == "DoneDocumentState":
                    return document
                if state == "ErrorDocumentState":
                    worker_log = document.get("workerLog")
                    raise DSWAPIError(
                        "Document generation failed"
                        + (f": {worker_log}" if isinstance(worker_log, str) and worker_log else "")
                    )
            time.sleep(poll_seconds)
        raise DSWAPIError("Timed out while waiting for final document generation")

    def get_document_download_url(self, document_uuid: str) -> str:
        """Get the download URL for one completed document."""

        payload = self._request_json("GET", f"/documents/{document_uuid}/download")
        url = payload.get("url")
        if not isinstance(url, str) or not url:
            raise DSWAPIError("Document download response did not include a valid URL")
        return url

    def download_url_text(self, url: str) -> str:
        """Download one rendered artifact as UTF-8 text."""

        download_url, headers = _apply_download_host_alias(url)
        response = self.session.get(
            download_url,
            headers=headers,
            verify=self.verify_ssl,
            timeout=60,
        )
        self._raise_for_status(response)
        return response.content.decode("utf-8", errors="replace")

    def _resolve_knowledge_model_package_bundle(self, bundle_path: Path) -> str:
        package_id = _read_knowledge_model_package_id_from_bundle(bundle_path)
        if package_id is not None:
            existing_uuid = self.find_knowledge_model_package_uuid_by_id(package_id)
            if existing_uuid is not None:
                return existing_uuid
        payload = self.upload_knowledge_model_package_bundle(bundle_path)
        resolved_uuid = payload.get("uuid")
        if not isinstance(resolved_uuid, str) or not resolved_uuid:
            raise DSWAPIError(
                f"KM bundle upload for {bundle_path} did not return a valid package UUID"
            )
        return resolved_uuid

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> requests.Response:
        url = f"{self.api_url}{endpoint}"
        headers = {"User-Agent": "dsw-document-template-tool"}
        if self.token is not None:
            headers["Authorization"] = f"Bearer {self.token}"
        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json,
            verify=self.verify_ssl,
            timeout=60,
        )
        return response

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        response = self._request(method, endpoint, params=params, json=json)
        self._raise_for_status(response, expected_statuses={expected_status})
        payload = response.json()
        if not isinstance(payload, dict):
            raise DSWAPIError(f"Expected JSON object from {endpoint}")
        return payload

    def _request_payload(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> Any:
        response = self._request(method, endpoint, params=params, json=json)
        self._raise_for_status(response, expected_statuses={expected_status})
        return response.json()

    @staticmethod
    def _raise_for_status(
        response: requests.Response,
        *,
        expected_statuses: set[int] | None = None,
    ) -> None:
        if expected_statuses is None:
            expected_statuses = {200}
        if response.status_code in expected_statuses:
            return
        try:
            payload = response.json()
        except Exception:
            payload = response.text
        raise DSWAPIError(
            f"Unexpected HTTP {response.status_code} for {response.request.method} "
            f"{response.request.url}: {payload}"
        )


UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def _looks_like_uuid(value: str) -> bool:
    return bool(UUID_PATTERN.match(value))


def _apply_download_host_alias(url: str) -> tuple[str, dict[str, str] | None]:
    """Rewrite a download URL host while preserving the signed Host header."""

    alias = os.environ.get("DSW_DOWNLOAD_HOST_ALIAS")
    if alias is None or "=" not in alias:
        return url, None
    source_host, target_host = (part.strip() for part in alias.split("=", 1))
    if not source_host or not target_host:
        return url, None

    parsed = urlsplit(url)
    if parsed.hostname != source_host:
        return url, None

    replacement_netloc = target_host
    if parsed.port is not None and ":" not in target_host:
        replacement_netloc = f"{target_host}:{parsed.port}"
    rewritten_url = urlunsplit(
        (
            parsed.scheme,
            replacement_netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
    return rewritten_url, {"Host": parsed.netloc}


def _read_knowledge_model_package_id_from_bundle(bundle_path: Path) -> str | None:
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    package_id = payload.get("id")
    if isinstance(package_id, str) and package_id.count(":") == 2:
        return package_id
    organization_id = payload.get("organizationId")
    km_id = payload.get("kmId")
    version = payload.get("version")
    if all(isinstance(item, str) and item for item in (organization_id, km_id, version)):
        return f"{organization_id}:{km_id}:{version}"
    return None
