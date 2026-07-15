"""Service for rendering one DSW project with a document template."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dsw_document_template_tool.api import DSWApiClient
from dsw_document_template_tool.tdk import (
    TemplateToolError,
    put_template_dir,
    read_local_template_coordinates,
    stage_local_template_dir,
    verify_template_dir,
)


@dataclass(frozen=True)
class ResolvedProject:
    """Project UUID resolved from an existing reference or created from events."""

    project_uuid: str
    created_by_tool: bool = False


def render_project(
    *,
    project_uuid: str | None,
    project_ref: Path,
    template_dir: Path,
    template_package: Path | None,
    output_path: Path,
    format_uuid: str,
    stage_id: str | None,
    api_url: str,
    api_key: str | None,
    email: str,
    password: str,
    tdk_executable: str,
    timeout_seconds: int,
    poll_seconds: float,
    verify_ssl: bool,
    keep_created_project: bool = False,
) -> Path:
    """Render one project with a draft source tree or released package zip."""

    template_dir = template_dir.resolve()
    template_package = template_package.resolve() if template_package is not None else None
    output_path = output_path.resolve()
    if template_package is None and not template_dir.is_dir():
        raise TemplateToolError(f"Template directory does not exist: {template_dir}")
    if template_package is not None and not template_package.is_file():
        raise TemplateToolError(f"Template package does not exist: {template_package}")

    client = DSWApiClient(api_url=api_url, verify_ssl=verify_ssl)
    staged_dir: Path | None = None
    resolved_project: ResolvedProject | None = None
    try:
        if api_key:
            client.set_token(api_key)
        else:
            client.login(email=email, password=password)
        if client.token is None:
            raise TemplateToolError("Authentication did not produce a DSW bearer token.")

        user = client.get_current_user()
        print(f"INFO: Authenticated as {user.get('name') or user.get('email')}")
        resolved_project = _resolve_or_create_project(
            client=client,
            project_uuid=project_uuid,
            project_ref=project_ref,
        )

        if template_package is not None:
            document, render_info = _render_released_template_package(
                client=client,
                package_path=template_package,
                project_uuid=resolved_project.project_uuid,
                format_uuid=format_uuid,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
            )
        else:
            document, render_info, staged_dir = _render_draft_template_dir(
                client=client,
                template_dir=template_dir,
                project_uuid=resolved_project.project_uuid,
                format_uuid=format_uuid,
                stage_id=stage_id,
                api_url=api_url,
                tdk_executable=tdk_executable,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
            )

        _write_rendered_document(
            output_path=output_path,
            document=document,
            metadata={
                "api_url": api_url,
                "project_uuid": resolved_project.project_uuid,
                "project_created_by_tool": resolved_project.created_by_tool,
                "format_uuid": format_uuid,
                "output": str(output_path),
                "bytes": len(document),
                **render_info,
            },
        )
        return output_path
    finally:
        if (
            resolved_project is not None
            and resolved_project.created_by_tool
            and not keep_created_project
        ):
            try:
                client.delete_project(resolved_project.project_uuid)
            except Exception as exc:
                print(
                    "WARNING: Failed to clean up created project "
                    f"{resolved_project.project_uuid}: {exc}"
                )
        client.close()
        if staged_dir is not None:
            shutil.rmtree(staged_dir.parent, ignore_errors=True)


def _render_draft_template_dir(
    *,
    client: DSWApiClient,
    template_dir: Path,
    project_uuid: str,
    format_uuid: str,
    stage_id: str | None,
    api_url: str,
    tdk_executable: str,
    timeout_seconds: int,
    poll_seconds: float,
) -> tuple[bytes, dict[str, object], Path]:
    staged_dir: Path | None = None
    try:
        source_coordinates = read_local_template_coordinates(template_dir)
        staged_dir, staged_coordinates = stage_local_template_dir(
            source_dir=template_dir,
            subject_label="project-render",
            stage_id=stage_id,
        )
        print(f"INFO: Verifying staged template {staged_coordinates.full_id}")
        verify_template_dir(executable=tdk_executable, template_dir=staged_dir)

        print(f"INFO: Uploading staged draft {staged_coordinates.full_id}")
        put_template_dir(
            executable=tdk_executable,
            template_dir=staged_dir,
            api_url=api_url,
            api_key=client.token,
        )

        draft_uuid = client.find_draft_uuid_by_id(staged_coordinates.full_id)
        if draft_uuid is None:
            raise TemplateToolError(
                f"Could not resolve uploaded draft UUID for {staged_coordinates.full_id}"
            )

        print(f"INFO: Rendering project {project_uuid} with draft {draft_uuid}")
        client.put_draft_preview_settings(
            draft_uuid=draft_uuid,
            format_uuid=format_uuid,
            project_uuid=project_uuid,
        )
        download_url = client.poll_draft_preview_url(
            draft_uuid=draft_uuid,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        return (
            client.download_url_bytes(download_url),
            {
                "mode": "draft_preview",
                "source_template_id": source_coordinates.full_id,
                "staged_template_id": staged_coordinates.full_id,
                "draft_uuid": draft_uuid,
            },
            staged_dir,
        )
    except Exception:
        if staged_dir is not None:
            shutil.rmtree(staged_dir.parent, ignore_errors=True)
        raise


def _render_released_template_package(
    *,
    client: DSWApiClient,
    package_path: Path,
    project_uuid: str,
    format_uuid: str,
    timeout_seconds: int,
    poll_seconds: float,
) -> tuple[bytes, dict[str, object]]:
    print(f"INFO: Importing released template package {package_path}")
    imported_template = client.upload_document_template_bundle(package_path)
    template_uuid = imported_template["uuid"]
    project_event_uuid = client.get_latest_project_event_uuid(project_uuid)
    print(f"INFO: Rendering project {project_uuid} with released template {template_uuid}")
    created_document = client.create_document(
        name=f"Render {package_path.stem}",
        project_uuid=project_uuid,
        document_template_uuid=template_uuid,
        format_uuid=format_uuid,
        project_event_uuid=project_event_uuid,
    )
    document_uuid = created_document.get("uuid")
    if not isinstance(document_uuid, str) or not document_uuid:
        raise TemplateToolError("DSW did not return a valid document UUID")
    client.poll_document_ready(
        project_uuid=project_uuid,
        document_uuid=document_uuid,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    download_url = client.get_document_download_url(document_uuid)
    return (
        client.download_url_bytes(download_url),
        {
            "mode": "released_package",
            "template_package": str(package_path),
            "document_template_uuid": template_uuid,
            "document_uuid": document_uuid,
            "project_event_uuid": project_event_uuid,
        },
    )


def _write_rendered_document(
    *,
    output_path: Path,
    document: bytes,
    metadata: dict[str, object],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(document)
    info_path = output_path.with_suffix(output_path.suffix + ".json")
    info_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"INFO: Wrote render metadata to {info_path}")


def _resolve_or_create_project(
    *,
    client: DSWApiClient,
    project_uuid: str | None,
    project_ref: Path,
) -> ResolvedProject:
    if project_uuid:
        return ResolvedProject(project_uuid=project_uuid)
    if project_ref.is_file():
        payload = json.loads(project_ref.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            ref_uuid = payload.get("project_uuid") or payload.get("uuid")
            if isinstance(ref_uuid, str) and ref_uuid:
                return ResolvedProject(project_uuid=ref_uuid)
            created_uuid = _create_project_from_ref_payload(
                client=client,
                project_ref=project_ref,
                payload=payload,
            )
            return ResolvedProject(project_uuid=created_uuid, created_by_tool=True)
    raise TemplateToolError(
        "Set --project-uuid, DSW_PROJECT_UUID, or a valid project reference at "
        f"{project_ref}. A project reference may contain `project_uuid`, or "
        "`knowledge_model_package_id` plus optional `events_file`."
    )


def _create_project_from_ref_payload(
    *,
    client: DSWApiClient,
    project_ref: Path,
    payload: dict[str, object],
) -> str:
    project_payload = payload.get("project")
    if isinstance(project_payload, dict):
        seed = {
            **project_payload,
            **{k: v for k, v in payload.items() if k != "project"},
        }
    else:
        seed = payload

    knowledge_model_package_id = seed.get("knowledge_model_package_id")
    if not isinstance(knowledge_model_package_id, str) or not knowledge_model_package_id:
        raise TemplateToolError(
            f"Project reference {project_ref} must define `knowledge_model_package_id` "
            "when it does not point at an existing project UUID."
        )

    project_ref_dir = project_ref.resolve().parent
    project_name = _optional_str(seed, "name") or project_ref.stem
    events_file = _optional_path(seed, "events_file", base_dir=project_ref_dir)
    knowledge_model_package_id = _resolve_path_value(
        knowledge_model_package_id,
        base_dir=project_ref_dir,
    )
    question_tag_uuids = seed.get("question_tag_uuids") or []
    if not isinstance(question_tag_uuids, list) or not all(
        isinstance(item, str) for item in question_tag_uuids
    ):
        raise TemplateToolError(
            f"Project reference {project_ref} has invalid `question_tag_uuids`."
        )

    print(f"INFO: Creating render project {project_name}")
    created_project = client.create_project_from_package(
        name=project_name,
        knowledge_model_package_id=knowledge_model_package_id,
        question_tag_uuids=question_tag_uuids,
        visibility=_optional_str(seed, "visibility") or "PrivateProjectVisibility",
        sharing=_optional_str(seed, "sharing") or "RestrictedProjectSharing",
    )
    created_uuid = created_project.get("uuid")
    if not isinstance(created_uuid, str) or not created_uuid:
        raise TemplateToolError(f"DSW did not return a valid project UUID for {project_ref}")

    if events_file is not None:
        try:
            events = _load_project_events(events_file)
            print(f"INFO: Applying {len(events)} project events from {events_file}")
            client.put_project_content(project_uuid=created_uuid, events=events)
        except Exception:
            client.delete_project(created_uuid)
            raise

    return created_uuid


def _load_project_events(events_file: Path) -> list[dict[str, Any]]:
    payload = json.loads(events_file.read_text(encoding="utf-8"))
    events = payload.get("events") if isinstance(payload, dict) else payload
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise TemplateToolError(
            "Project events file must contain a JSON list or an object with an "
            f"`events` list: {events_file}"
        )
    return events


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _optional_path(payload: dict[str, object], key: str, *, base_dir: Path) -> Path | None:
    value = _optional_str(payload, key)
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    if not path.is_file():
        raise TemplateToolError(f"Project reference points at missing `{key}` file: {path}")
    return path.resolve()


def _resolve_path_value(value: str, *, base_dir: Path) -> str:
    path = Path(value).expanduser()
    if path.is_absolute():
        return str(path) if path.is_file() else value
    relative_path = base_dir / path
    if relative_path.is_file():
        return str(relative_path.resolve())
    return value
