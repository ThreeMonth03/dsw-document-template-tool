"""Tests for project-reference resolution used by render-project."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dsw_document_template_tool.render_project import (
    _load_project_events,
    _resolve_or_create_project,
)


class FakeDSWClient:
    """Small stand-in for the DSW API client used by render-project."""

    def __init__(self) -> None:
        self.created_projects: list[dict[str, Any]] = []
        self.applied_events: list[tuple[str, list[dict[str, Any]]]] = []
        self.deleted_projects: list[str] = []

    def create_project_from_package(
        self,
        *,
        name: str,
        knowledge_model_package_id: str,
        question_tag_uuids: list[str],
        visibility: str,
        sharing: str,
    ) -> dict[str, str]:
        self.created_projects.append(
            {
                "name": name,
                "knowledge_model_package_id": knowledge_model_package_id,
                "question_tag_uuids": question_tag_uuids,
                "visibility": visibility,
                "sharing": sharing,
            }
        )
        return {"uuid": "11111111-1111-4111-8111-111111111111"}

    def put_project_content(self, *, project_uuid: str, events: list[dict[str, Any]]) -> None:
        self.applied_events.append((project_uuid, events))

    def delete_project(self, project_uuid: str) -> None:
        self.deleted_projects.append(project_uuid)


def test_project_ref_can_point_at_existing_project_uuid(tmp_path: Path) -> None:
    """Existing project refs should not create or mutate local DSW projects."""

    project_ref = tmp_path / "project.json"
    project_ref.write_text(
        json.dumps({"project_uuid": "22222222-2222-4222-8222-222222222222"}),
        encoding="utf-8",
    )
    client = FakeDSWClient()

    resolved = _resolve_or_create_project(
        client=client,
        project_uuid=None,
        project_ref=project_ref,
    )

    assert resolved.project_uuid == "22222222-2222-4222-8222-222222222222"
    assert resolved.created_by_tool is False
    assert client.created_projects == []
    assert client.applied_events == []


def test_project_ref_can_create_project_from_events(tmp_path: Path) -> None:
    """Project refs with KM/events data should be copied into the target DSW."""

    events_file = tmp_path / "project.events.json"
    km_file = tmp_path / "root-zh-hant.km"
    project_ref = tmp_path / "project.json"
    events = [{"uuid": "event-1", "eventType": "SetReplyEvent"}]
    events_file.write_text(json.dumps(events), encoding="utf-8")
    km_file.write_text("{}", encoding="utf-8")
    project_ref.write_text(
        json.dumps(
            {
                "name": "fixture project",
                "knowledge_model_package_id": "root-zh-hant.km",
                "events_file": "project.events.json",
                "question_tag_uuids": ["tag-1"],
            }
        ),
        encoding="utf-8",
    )
    client = FakeDSWClient()

    resolved = _resolve_or_create_project(
        client=client,
        project_uuid=None,
        project_ref=project_ref,
    )

    assert resolved.project_uuid == "11111111-1111-4111-8111-111111111111"
    assert resolved.created_by_tool is True
    assert client.created_projects == [
        {
            "name": "fixture project",
            "knowledge_model_package_id": str(km_file.resolve()),
            "question_tag_uuids": ["tag-1"],
            "visibility": "PrivateProjectVisibility",
            "sharing": "RestrictedProjectSharing",
        }
    ]
    assert client.applied_events == [(resolved.project_uuid, events)]


def test_project_events_loader_accepts_wrapped_events_payload(tmp_path: Path) -> None:
    """Exported project payloads may wrap events in an `events` key."""

    events_file = tmp_path / "project.events.json"
    events = [{"uuid": "event-1", "eventType": "SetReplyEvent"}]
    events_file.write_text(json.dumps({"events": events}), encoding="utf-8")

    assert _load_project_events(events_file) == events
