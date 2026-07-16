"""Tests for workflow orchestration helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from dsw_document_template_tool._regression import parallel as regression_parallel
from dsw_document_template_tool.models import (
    DocumentTemplateReference,
    FixtureConfig,
    FixtureProject,
    ProjectSeedConfig,
    RegressionConfig,
    ResolvedSubject,
    SubjectConfig,
)
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


class _FakePackageClient:
    """Record released package uploads."""

    def __init__(self) -> None:
        self.uploaded: list[Path] = []

    def upload_document_template_bundle_reference(
        self,
        package_path: Path,
    ) -> DocumentTemplateReference:
        self.uploaded.append(package_path)
        return DocumentTemplateReference(template_id="dsw:translated:1.0.0")


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


def test_local_package_subject_uploads_the_actual_release_asset(tmp_path: Path) -> None:
    """Package regression should import the zip that users download."""

    package_path = tmp_path / "translated-template.zip"
    package_path.write_bytes(b"package")
    client = _FakePackageClient()

    resolved = DocumentTemplateWorkflowService()._resolve_local_package_subject(
        client=client,
        label="candidate",
        subject=SubjectConfig(kind="local_package", value=str(package_path)),
    )

    assert client.uploaded == [package_path.resolve()]
    assert resolved.mode == "released"
    assert resolved.display_id == "dsw:translated:1.0.0"
    assert resolved.template_reference == DocumentTemplateReference(
        template_id="dsw:translated:1.0.0"
    )


def test_render_success_assertion_renders_only_the_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Translated-package validation should render once instead of self-comparing."""

    service = DocumentTemplateWorkflowService()
    rendered_subjects: list[str] = []

    def fake_render_subject_html(**kwargs) -> str:
        rendered_subjects.append(kwargs["subject"].label)
        return "<p>translated</p>"

    monkeypatch.setattr(service, "_render_subject_html", fake_render_subject_html)
    regression = RegressionConfig(
        assertion="render_success",
        mode="document",
        format_uuid="format-uuid",
        output_dir=tmp_path,
        timeout_seconds=30,
        poll_seconds=0.1,
        cleanup_projects=True,
        ignore_patterns=[],
    )
    candidate = ResolvedSubject(
        label="candidate",
        mode="released",
        source_value="translated-template.zip",
        display_id="dsw:translated:1.0.0",
        template_reference=DocumentTemplateReference(template_id="dsw:translated:1.0.0"),
    )

    result = service._run_fixture_assertion(
        client=object(),
        config=SimpleNamespace(regression=regression),
        fixture=FixtureConfig(name="translated-package"),
        resolved_fixture=FixtureProject(
            name="translated-package",
            project_uuid="project-uuid",
            project_event_uuid=None,
            created_by_tool=False,
        ),
        baseline=None,
        candidate=candidate,
    )

    assert rendered_subjects == ["candidate"]
    assert result.passed is True
    assert result.baseline is None
    assert result.candidate.raw_path.read_text(encoding="utf-8") == "<p>translated</p>"
