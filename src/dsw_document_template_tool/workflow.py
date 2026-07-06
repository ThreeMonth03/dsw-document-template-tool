"""End-to-end headless workflow for DSW document template regression."""

from __future__ import annotations

import json
import shutil
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .api import DSWApiClient, DSWAPIError
from .config import load_workflow_config
from .fixture_generator import generate_questionnaire_events
from .html_diff import build_unified_diff, normalize_html
from .models import (
    FixtureConfig,
    FixtureProject,
    FixtureRegressionResult,
    GeneratedFixtureConfig,
    RegressionReport,
    RenderArtifact,
    ResolvedSubject,
    SubjectConfig,
    WorkflowConfig,
)
from .tdk import (
    TemplateToolError,
    parse_template_coordinates,
    put_template_dir,
    stage_local_template_dir,
    verify_template_dir,
)


class DocumentTemplateWorkflowService:
    """High-level service that performs headless regression comparisons."""

    def run(self, config_path: str | Path) -> RegressionReport:
        """Load config and execute the full regression workflow."""

        config = load_workflow_config(config_path)
        config.regression.output_dir.mkdir(parents=True, exist_ok=True)

        client = DSWApiClient(
            api_url=config.api.url,
            verify_ssl=config.api.verify_ssl,
        )
        created_projects: list[FixtureProject] = []
        staged_dirs: list[Path] = []
        try:
            self._authenticate(client, config)
            user = client.get_current_user()
            print(f"INFO: Authenticated as {user.get('name') or user.get('email')}")

            baseline = self._resolve_subject(
                client=client,
                config=config,
                label="baseline",
                subject=config.baseline,
                staged_dirs=staged_dirs,
            )
            candidate = self._resolve_subject(
                client=client,
                config=config,
                label="candidate",
                subject=config.candidate,
                staged_dirs=staged_dirs,
            )

            fixture_results: list[FixtureRegressionResult] = []
            fixture_results.extend(
                self._run_configured_fixtures(
                    client=client,
                    config=config,
                    baseline=baseline,
                    candidate=candidate,
                    created_projects=created_projects,
                )
            )
            fixture_results.extend(
                self._run_generated_fixtures(
                    client=client,
                    config=config,
                    baseline=baseline,
                    candidate=candidate,
                    created_projects=created_projects,
                )
            )

            passed = all(result.equal for result in fixture_results)
            report_path = config.regression.output_dir / "regression_report.json"
            report = RegressionReport(
                mode=config.regression.mode,
                output_dir=config.regression.output_dir,
                passed=passed,
                fixture_results=fixture_results,
                report_path=report_path,
            )
            report_path.write_text(
                json.dumps(self._serialize_report(report), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return report
        finally:
            self._cleanup_projects(
                client=client,
                cleanup_projects=config.regression.cleanup_projects,
                created_projects=created_projects,
            )
            client.close()
            self._cleanup_staged_dirs(staged_dirs)

    def _run_configured_fixtures(
        self,
        *,
        client: DSWApiClient,
        config: WorkflowConfig,
        baseline: ResolvedSubject,
        candidate: ResolvedSubject,
        created_projects: list[FixtureProject],
    ) -> list[FixtureRegressionResult]:
        fixture_results: list[FixtureRegressionResult] = []
        for fixture in config.fixtures:
            resolved_fixture = self._prepare_fixture(
                client=client,
                fixture=fixture,
                cleanup_projects=config.regression.cleanup_projects,
            )
            if resolved_fixture.created_by_tool:
                created_projects.append(resolved_fixture)
            fixture_results.append(
                self._compare_fixture(
                    client=client,
                    config=config,
                    fixture=fixture,
                    resolved_fixture=resolved_fixture,
                    baseline=baseline,
                    candidate=candidate,
                )
            )
        return fixture_results

    def _run_generated_fixtures(
        self,
        *,
        client: DSWApiClient,
        config: WorkflowConfig,
        baseline: ResolvedSubject,
        candidate: ResolvedSubject,
        created_projects: list[FixtureProject],
    ) -> list[FixtureRegressionResult]:
        fixture_results: list[FixtureRegressionResult] = []
        for generated_fixture in config.generated_fixtures:
            for case_index in range(generated_fixture.count):
                fixture, resolved_fixture = self._prepare_generated_fixture(
                    client=client,
                    config=config,
                    generated_fixture=generated_fixture,
                    case_index=case_index,
                )
                if resolved_fixture.created_by_tool:
                    created_projects.append(resolved_fixture)
                fixture_results.append(
                    self._compare_fixture(
                        client=client,
                        config=config,
                        fixture=fixture,
                        resolved_fixture=resolved_fixture,
                        baseline=baseline,
                        candidate=candidate,
                    )
                )
        return fixture_results

    def _cleanup_projects(
        self,
        *,
        client: DSWApiClient,
        cleanup_projects: bool,
        created_projects: list[FixtureProject],
    ) -> None:
        if not cleanup_projects:
            return
        for fixture_project in reversed(created_projects):
            try:
                client.delete_project(fixture_project.project_uuid)
            except Exception as exc:
                print(f"WARNING: Failed to clean up project {fixture_project.project_uuid}: {exc}")

    @staticmethod
    def _cleanup_staged_dirs(staged_dirs: list[Path]) -> None:
        for staged_dir in staged_dirs:
            try:
                shutil.rmtree(staged_dir.parent)
            except Exception:
                pass

    def _authenticate(self, client: DSWApiClient, config: WorkflowConfig) -> None:
        if config.api.token is not None:
            client.set_token(config.api.token)
            return
        assert config.api.email is not None
        assert config.api.password is not None
        client.login(email=config.api.email, password=config.api.password)

    def _resolve_subject(
        self,
        *,
        client: DSWApiClient,
        config: WorkflowConfig,
        label: str,
        subject: SubjectConfig,
        staged_dirs: list[Path],
    ) -> ResolvedSubject:
        print(f"INFO: Resolving {label} subject ({subject.kind})")

        if subject.kind == "local_dir":
            return self._resolve_local_subject(
                client=client,
                config=config,
                label=label,
                subject=subject,
                staged_dirs=staged_dirs,
            )

        if subject.kind == "draft_id":
            return self._resolve_draft_subject(client=client, label=label, subject=subject)

        if subject.kind == "released_id":
            return self._resolve_released_subject(client=client, label=label, subject=subject)

        raise TemplateToolError(f"Unsupported subject kind {subject.kind!r}")

    def _resolve_local_subject(
        self,
        *,
        client: DSWApiClient,
        config: WorkflowConfig,
        label: str,
        subject: SubjectConfig,
        staged_dirs: list[Path],
    ) -> ResolvedSubject:
        local_dir = Path(subject.value).resolve()
        staged_dir, staged_coordinates = stage_local_template_dir(
            source_dir=local_dir,
            subject_label=label,
            stage_id=subject.stage_id,
        )
        staged_dirs.append(staged_dir)
        if subject.verify:
            print(f"INFO: Verifying staged template {staged_coordinates.full_id}")
            verify_template_dir(
                executable=config.tdk.executable,
                template_dir=staged_dir,
            )
        print(f"INFO: Uploading staged draft {staged_coordinates.full_id}")
        if client.token is None:
            raise TemplateToolError(
                "Local template upload requires a bearer token, but login did not produce one."
            )
        put_template_dir(
            executable=config.tdk.executable,
            template_dir=staged_dir,
            api_url=config.api.url,
            api_key=client.token,
        )
        draft_uuid = client.find_draft_uuid_by_id(staged_coordinates.full_id)
        if draft_uuid is None:
            raise TemplateToolError(
                f"Could not resolve uploaded draft UUID for {staged_coordinates.full_id}"
            )
        return ResolvedSubject(
            label=label,
            mode="draft",
            source_value=subject.value,
            display_id=staged_coordinates.full_id,
            draft_uuid=draft_uuid,
            local_dir=local_dir,
            staged_dir=staged_dir,
        )

    def _resolve_draft_subject(
        self,
        *,
        client: DSWApiClient,
        label: str,
        subject: SubjectConfig,
    ) -> ResolvedSubject:
        draft_uuid = self._draft_uuid_for_subject(client=client, subject=subject)
        if draft_uuid is None:
            raise DSWAPIError(f"Could not resolve draft subject {subject.value!r}")
        return ResolvedSubject(
            label=label,
            mode="draft",
            source_value=subject.value,
            display_id=subject.value,
            draft_uuid=draft_uuid,
        )

    @staticmethod
    def _draft_uuid_for_subject(
        *,
        client: DSWApiClient,
        subject: SubjectConfig,
    ) -> str | None:
        if subject.value.count(":") == 2:
            return client.find_draft_uuid_by_id(subject.value)
        if client.check_draft_exists(subject.value):
            return subject.value
        return None

    def _resolve_released_subject(
        self,
        *,
        client: DSWApiClient,
        label: str,
        subject: SubjectConfig,
    ) -> ResolvedSubject:
        parse_template_coordinates(subject.value)
        template_uuid = client.resolve_document_template_uuid(subject.value)
        return ResolvedSubject(
            label=label,
            mode="released",
            source_value=subject.value,
            display_id=subject.value,
            template_id=subject.value,
            template_uuid=template_uuid,
        )

    def _prepare_fixture(
        self,
        *,
        client: DSWApiClient,
        fixture: FixtureConfig,
        cleanup_projects: bool,
    ) -> FixtureProject:
        if fixture.project_uuid is not None:
            project_uuid = fixture.project_uuid
            created = False
        else:
            assert fixture.project is not None
            unique_name = f"{fixture.project.name} [{uuid.uuid4().hex[:8]}]"
            print(f"INFO: Creating fixture project {unique_name}")
            payload = client.create_project_from_package(
                name=unique_name,
                knowledge_model_package_id=fixture.project.knowledge_model_package_id,
                question_tag_uuids=fixture.project.question_tag_uuids,
                visibility=fixture.project.visibility,
                sharing=fixture.project.sharing,
            )
            project_uuid = str(payload["uuid"])
            created = True

        if fixture.events_file is not None:
            events = self._load_events(fixture.events_file)
            print(f"INFO: Applying {len(events)} fixture events to {project_uuid}")
            client.put_project_content(project_uuid=project_uuid, events=events)
            if fixture.project_event_uuid is None:
                project_event_uuid = client.get_latest_project_event_uuid(project_uuid)
            else:
                project_event_uuid = fixture.project_event_uuid
        else:
            project_event_uuid = fixture.project_event_uuid

        return FixtureProject(
            name=fixture.name,
            project_uuid=project_uuid,
            project_event_uuid=project_event_uuid,
            created_by_tool=created and cleanup_projects,
        )

    def _prepare_generated_fixture(
        self,
        *,
        client: DSWApiClient,
        config: WorkflowConfig,
        generated_fixture: GeneratedFixtureConfig,
        case_index: int,
    ) -> tuple[FixtureConfig, FixtureProject]:
        fixture_name = f"{generated_fixture.name_prefix}-{case_index:03d}"
        fixture = FixtureConfig(
            name=fixture_name,
            project=generated_fixture.project,
        )
        project_name = f"{generated_fixture.project.name} {case_index:03d}"
        unique_name = f"{project_name} [{uuid.uuid4().hex[:8]}]"
        print(f"INFO: Creating generated fixture project {unique_name}")
        payload = client.create_project_from_package(
            name=unique_name,
            knowledge_model_package_id=generated_fixture.project.knowledge_model_package_id,
            question_tag_uuids=generated_fixture.project.question_tag_uuids,
            visibility=generated_fixture.project.visibility,
            sharing=generated_fixture.project.sharing,
        )
        project_uuid = str(payload["uuid"])
        try:
            questionnaire = client.get_project_questionnaire(project_uuid)
            generated = generate_questionnaire_events(
                questionnaire,
                seed=generated_fixture.seed,
                case_index=case_index,
                max_events=generated_fixture.max_events,
                max_items_per_list=generated_fixture.max_items_per_list,
                answer_probability=generated_fixture.answer_probability,
            )
            fixture_output_dir = config.regression.output_dir / fixture_name
            fixture_output_dir.mkdir(parents=True, exist_ok=True)
            (fixture_output_dir / "fixture.events.json").write_text(
                json.dumps(generated.events, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (fixture_output_dir / "fixture.stats.json").write_text(
                json.dumps(generated.stats, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(
                f"INFO: Applying {len(generated.events)} generated fixture events to {project_uuid}"
            )
            client.put_project_content(project_uuid=project_uuid, events=generated.events)
            project_event_uuid = client.get_latest_project_event_uuid(project_uuid)
        except Exception:
            if config.regression.cleanup_projects:
                try:
                    client.delete_project(project_uuid)
                except Exception as exc:
                    print(f"WARNING: Failed to clean up project {project_uuid}: {exc}")
            raise
        return (
            fixture,
            FixtureProject(
                name=fixture.name,
                project_uuid=project_uuid,
                project_event_uuid=project_event_uuid,
                created_by_tool=config.regression.cleanup_projects,
            ),
        )

    def _compare_fixture(
        self,
        *,
        client: DSWApiClient,
        config: WorkflowConfig,
        fixture: FixtureConfig,
        resolved_fixture: FixtureProject,
        baseline: ResolvedSubject,
        candidate: ResolvedSubject,
    ) -> FixtureRegressionResult:
        fixture_output_dir = config.regression.output_dir / fixture.name
        fixture_output_dir.mkdir(parents=True, exist_ok=True)

        if config.regression.mode == "preview":
            if baseline.mode != "draft" or candidate.mode != "draft":
                raise TemplateToolError(
                    "Preview mode requires both subjects to resolve to draft templates"
                )
            baseline_html, candidate_html = self._render_subjects_in_parallel(
                client=client,
                baseline_render=lambda render_client: self._render_preview_html(
                    client=render_client,
                    draft_uuid=baseline.draft_uuid or "",
                    project_uuid=resolved_fixture.project_uuid,
                    format_uuid=config.regression.format_uuid,
                    timeout_seconds=config.regression.timeout_seconds,
                    poll_seconds=config.regression.poll_seconds,
                ),
                candidate_render=lambda render_client: self._render_preview_html(
                    client=render_client,
                    draft_uuid=candidate.draft_uuid or "",
                    project_uuid=resolved_fixture.project_uuid,
                    format_uuid=config.regression.format_uuid,
                    timeout_seconds=config.regression.timeout_seconds,
                    poll_seconds=config.regression.poll_seconds,
                ),
            )
        elif config.regression.mode == "document":
            if baseline.mode != "released" or candidate.mode != "released":
                raise TemplateToolError(
                    "Document mode requires both subjects to be released template IDs"
                )
            baseline_html, candidate_html = self._render_subjects_in_parallel(
                client=client,
                baseline_render=lambda render_client: self._render_document_html(
                    client=render_client,
                    project_uuid=resolved_fixture.project_uuid,
                    project_event_uuid=resolved_fixture.project_event_uuid,
                    template_uuid=baseline.template_uuid or "",
                    format_uuid=config.regression.format_uuid,
                    timeout_seconds=config.regression.timeout_seconds,
                    poll_seconds=config.regression.poll_seconds,
                    name=f"{fixture.name}-{baseline.label}",
                ),
                candidate_render=lambda render_client: self._render_document_html(
                    client=render_client,
                    project_uuid=resolved_fixture.project_uuid,
                    project_event_uuid=resolved_fixture.project_event_uuid,
                    template_uuid=candidate.template_uuid or "",
                    format_uuid=config.regression.format_uuid,
                    timeout_seconds=config.regression.timeout_seconds,
                    poll_seconds=config.regression.poll_seconds,
                    name=f"{fixture.name}-{candidate.label}",
                ),
            )
        else:
            raise TemplateToolError(f"Unsupported regression mode {config.regression.mode!r}")

        baseline_artifact = self._write_artifact(
            fixture_output_dir=fixture_output_dir,
            subject=baseline,
            raw_html=baseline_html,
            ignore_patterns=config.regression.ignore_patterns,
        )
        candidate_artifact = self._write_artifact(
            fixture_output_dir=fixture_output_dir,
            subject=candidate,
            raw_html=candidate_html,
            ignore_patterns=config.regression.ignore_patterns,
        )

        baseline_normalized = baseline_artifact.normalized_path.read_text(encoding="utf-8")
        candidate_normalized = candidate_artifact.normalized_path.read_text(encoding="utf-8")
        equal = baseline_normalized == candidate_normalized
        diff_path = None
        if not equal:
            diff_path = fixture_output_dir / "diff.diff"
            diff_path.write_text(
                build_unified_diff(
                    baseline_normalized,
                    candidate_normalized,
                    baseline_label=baseline.display_id,
                    candidate_label=candidate.display_id,
                )
                + "\n",
                encoding="utf-8",
            )
            print(f"FAILURE: Mismatch detected for fixture {fixture.name}")
        else:
            print(f"SUCCESS: Fixture {fixture.name} matched after normalization")

        return FixtureRegressionResult(
            fixture_name=fixture.name,
            project_uuid=resolved_fixture.project_uuid,
            equal=equal,
            baseline=baseline_artifact,
            candidate=candidate_artifact,
            diff_path=diff_path,
        )

    def _render_preview_html(
        self,
        *,
        client: DSWApiClient,
        draft_uuid: str,
        project_uuid: str,
        format_uuid: str,
        timeout_seconds: int,
        poll_seconds: float,
    ) -> str:
        client.put_draft_preview_settings(
            draft_uuid=draft_uuid,
            format_uuid=format_uuid,
            project_uuid=project_uuid,
        )
        url = client.poll_draft_preview_url(
            draft_uuid=draft_uuid,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        return client.download_url_text(url)

    def _render_document_html(
        self,
        *,
        client: DSWApiClient,
        project_uuid: str,
        project_event_uuid: str | None,
        template_uuid: str,
        format_uuid: str,
        timeout_seconds: int,
        poll_seconds: float,
        name: str,
    ) -> str:
        created_document = client.create_document(
            name=name,
            project_uuid=project_uuid,
            document_template_uuid=template_uuid,
            format_uuid=format_uuid,
            project_event_uuid=project_event_uuid,
        )
        document_uuid = str(created_document["uuid"])
        client.poll_document_ready(
            project_uuid=project_uuid,
            document_uuid=document_uuid,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        url = client.get_document_download_url(document_uuid)
        return client.download_url_text(url)

    def _write_artifact(
        self,
        *,
        fixture_output_dir: Path,
        subject: ResolvedSubject,
        raw_html: str,
        ignore_patterns: list[str],
    ) -> RenderArtifact:
        raw_path = fixture_output_dir / f"{subject.label}.raw.html"
        normalized_path = fixture_output_dir / f"{subject.label}.normalized.html"
        raw_path.write_text(raw_html, encoding="utf-8")
        normalized_path.write_text(
            normalize_html(raw_html, ignore_patterns=ignore_patterns) + "\n",
            encoding="utf-8",
        )
        return RenderArtifact(
            raw_path=raw_path,
            normalized_path=normalized_path,
            subject_label=subject.label,
            template_reference=subject.display_id,
        )

    def _render_subjects_in_parallel(
        self,
        *,
        client: DSWApiClient,
        baseline_render: Callable[[DSWApiClient], str],
        candidate_render: Callable[[DSWApiClient], str],
    ) -> tuple[str, str]:
        def run_isolated(render: Callable[[DSWApiClient], str]) -> str:
            render_client = self._clone_authenticated_client(client)
            try:
                return render(render_client)
            finally:
                render_client.close()

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="dsw-render") as executor:
            baseline_future = executor.submit(run_isolated, baseline_render)
            candidate_future = executor.submit(run_isolated, candidate_render)
            return baseline_future.result(), candidate_future.result()

    @staticmethod
    def _clone_authenticated_client(client: DSWApiClient) -> DSWApiClient:
        if client.token is None:
            raise TemplateToolError("Parallel render requires an authenticated DSW client")
        render_client = DSWApiClient(
            api_url=client.api_url,
            verify_ssl=client.verify_ssl,
        )
        render_client.set_token(client.token)
        return render_client

    @staticmethod
    def _load_events(path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("events")
        if not isinstance(payload, list):
            raise TemplateToolError(f"Expected event list in {path}")
        events: list[dict[str, Any]] = []
        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                raise TemplateToolError(f"Event #{index} in {path} must be a JSON object")
            events.append(item)
        return events

    @staticmethod
    def _serialize_report(report: RegressionReport) -> dict[str, Any]:
        return {
            "mode": report.mode,
            "output_dir": str(report.output_dir),
            "passed": report.passed,
            "fixtures": [
                {
                    "fixture_name": result.fixture_name,
                    "project_uuid": result.project_uuid,
                    "equal": result.equal,
                    "baseline": {
                        "subject_label": result.baseline.subject_label,
                        "template_reference": result.baseline.template_reference,
                        "raw_path": str(result.baseline.raw_path),
                        "normalized_path": str(result.baseline.normalized_path),
                    },
                    "candidate": {
                        "subject_label": result.candidate.subject_label,
                        "template_reference": result.candidate.template_reference,
                        "raw_path": str(result.candidate.raw_path),
                        "normalized_path": str(result.candidate.normalized_path),
                    },
                    "diff_path": None if result.diff_path is None else str(result.diff_path),
                }
                for result in report.fixture_results
            ],
        }
