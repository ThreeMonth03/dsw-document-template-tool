"""Tests for workflow orchestration helpers."""

from __future__ import annotations

import json
from pathlib import Path

from dsw_document_template_tool._regression import parallel as regression_parallel
from dsw_document_template_tool.models import FixtureConfig, ProjectSeedConfig
from dsw_document_template_tool.workflow import DocumentTemplateWorkflowService


class _FakeRenderClient:
    def __init__(self, label: str):
        self.label = label
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeFixtureClient:
    """Record fixture creation and content import calls."""

    def __init__(self) -> None:
        self.applied_events: list[tuple[str, list[dict[str, str]]]] = []

    def create_project_from_package(self, **kwargs) -> dict[str, str]:
        return {"uuid": "11111111-1111-4111-8111-111111111111"}

    def put_project_content(
        self,
        *,
        project_uuid: str,
        events: list[dict[str, str]],
    ) -> None:
        self.applied_events.append((project_uuid, events))


def test_render_subjects_in_parallel_uses_isolated_clients(monkeypatch) -> None:
    """Baseline and candidate renders should not share one requests session."""

    main_client = object()
    created_clients: list[_FakeRenderClient] = []
    seen_clients: list[tuple[str, _FakeRenderClient]] = []

    def clone_client(client):
        assert client is main_client
        render_client = _FakeRenderClient(f"render-{len(created_clients)}")
        created_clients.append(render_client)
        return render_client

    def render(label: str):
        def render_(client: _FakeRenderClient) -> str:
            seen_clients.append((label, client))
            return f"{label}:{client.label}"

        return render_

    monkeypatch.setattr(regression_parallel, "clone_authenticated_client", clone_client)

    baseline_html, candidate_html = regression_parallel.render_subjects_in_parallel(
        client=main_client,
        baseline_render=render("baseline"),
        candidate_render=render("candidate"),
    )

    assert baseline_html.startswith("baseline:render-")
    assert candidate_html.startswith("candidate:render-")
    assert len(created_clients) == 2
    assert len({id(client) for _, client in seen_clients}) == 2
    assert all(client.closed for client in created_clients)


def test_events_fixture_renders_current_project_without_snapshot(tmp_path: Path) -> None:
    """Bulk event imports should use the complete current project state."""

    events_path = tmp_path / "fixture.events.json"
    events = [{"uuid": "event-1", "type": "SetReplyEvent"}]
    events_path.write_text(json.dumps(events), encoding="utf-8")
    fixture = FixtureConfig(
        name="filled-project",
        project=ProjectSeedConfig(
            name="filled project",
            knowledge_model_package_id="dsw:root:2.7.0",
        ),
        events_file=events_path,
    )
    client = _FakeFixtureClient()

    resolved = DocumentTemplateWorkflowService()._prepare_fixture(
        client=client,
        fixture=fixture,
        cleanup_projects=True,
    )

    assert client.applied_events == [(resolved.project_uuid, events)]
    assert resolved.project_event_uuid is None
