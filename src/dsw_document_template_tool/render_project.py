#!/usr/bin/env python3
"""Render one already-filled DSW project with a local document template."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
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

DEFAULT_API_URL = "http://localhost:3000/wizard-api"
DEFAULT_EMAIL = "albert.einstein@example.com"
DEFAULT_PASSWORD = "password"
DEFAULT_TDK_EXECUTABLE = ".venv/bin/dsw-tdk"
DEFAULT_TEMPLATE_DIR = (
    "outputs/document-templates/dsw-science-europe/v1.30.0/zh-Hant/"
    "dsw-science-europe-zh-hant-1.30.0"
)
DEFAULT_PROJECT_REF = "workspace/projects/test-project.json"
DEFAULT_OUTPUT = "outputs/project-render/dsw-science-europe/v1.30.0/zh-Hant/test-project.pdf"
PDF_FORMAT_UUID = "68c26e34-5e77-4e15-9bf7-06ff92582257"


@dataclass(frozen=True)
class ResolvedProject:
    """Project UUID resolved from an existing reference or created from events."""

    project_uuid: str
    created_by_tool: bool = False


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(
        description=("Render an existing or fixture DSW project with a local template draft."),
    )
    parser.add_argument(
        "--project-uuid",
        default=os.environ.get("DSW_PROJECT_UUID"),
        help="Existing DSW project UUID. Defaults to DSW_PROJECT_UUID, then --project-ref.",
    )
    parser.add_argument(
        "--project-ref",
        default=os.environ.get("DSW_PROJECT_REF", DEFAULT_PROJECT_REF),
        help=(
            "JSON project reference file used when --project-uuid is omitted. "
            "It may point at an existing project UUID or define a KM/events recipe."
        ),
    )
    parser.add_argument(
        "--template-dir",
        default=os.environ.get("DSW_TEMPLATE_DIR", DEFAULT_TEMPLATE_DIR),
        help="Local document template directory to upload as a draft.",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("DSW_RENDER_OUTPUT", DEFAULT_OUTPUT),
        help="File path for the downloaded rendered document.",
    )
    parser.add_argument(
        "--format-uuid",
        default=os.environ.get("DSW_FORMAT_UUID", PDF_FORMAT_UUID),
        help="DSW document format UUID, defaults to PDF.",
    )
    parser.add_argument(
        "--stage-id",
        default=os.environ.get("DSW_STAGE_ID"),
        help="Optional staged draft coordinates in org:template:version form.",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("DSW_API_URL", DEFAULT_API_URL),
        help="DSW wizard API URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DSW_API_KEY"),
        help="Existing DSW bearer token. If omitted, email/password login is used.",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("DSW_EMAIL", DEFAULT_EMAIL),
        help="DSW user email for login when --api-key is omitted.",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("DSW_PASSWORD", DEFAULT_PASSWORD),
        help="DSW password for login when --api-key is omitted.",
    )
    parser.add_argument(
        "--tdk-executable",
        default=os.environ.get("DSW_TDK", DEFAULT_TDK_EXECUTABLE),
        help="Path to dsw-tdk executable.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.environ.get("DSW_RENDER_TIMEOUT_SECONDS", "240")),
        help="Maximum seconds to wait for document generation.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=float(os.environ.get("DSW_RENDER_POLL_SECONDS", "1.0")),
        help="Seconds between preview status polls.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip dsw-tdk verify before uploading the staged draft.",
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=_env_bool("DSW_VERIFY_SSL", default=False),
        help="Verify TLS certificates for DSW API requests.",
    )
    parser.add_argument(
        "--keep-created-project",
        action="store_true",
        default=_env_bool("DSW_KEEP_CREATED_PROJECT", default=False),
        help="Keep a project created from --project-ref instead of deleting it after render.",
    )
    return parser


def main() -> None:
    """Render the selected project and exit non-zero on failures."""

    args = build_argument_parser().parse_args()
    try:
        output_path = render_project(
            project_uuid=args.project_uuid,
            project_ref=Path(args.project_ref),
            template_dir=Path(args.template_dir),
            output_path=Path(args.output),
            format_uuid=args.format_uuid,
            stage_id=args.stage_id,
            api_url=args.api_url,
            api_key=args.api_key,
            email=args.email,
            password=args.password,
            tdk_executable=args.tdk_executable,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
            skip_verify=args.skip_verify,
            verify_ssl=args.verify_ssl,
            keep_created_project=args.keep_created_project,
        )
    except Exception as exc:
        print(f"FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"SUCCESS: Wrote rendered project document to {output_path}")


def render_project(
    *,
    project_uuid: str | None,
    project_ref: Path,
    template_dir: Path,
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
    skip_verify: bool,
    verify_ssl: bool,
    keep_created_project: bool = False,
) -> Path:
    """Upload a local template as a draft preview and render one project."""

    template_dir = template_dir.resolve()
    output_path = output_path.resolve()
    if not template_dir.is_dir():
        raise TemplateToolError(f"Template directory does not exist: {template_dir}")

    source_coordinates = read_local_template_coordinates(template_dir)
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

        staged_dir, staged_coordinates = stage_local_template_dir(
            source_dir=template_dir,
            subject_label="project-render",
            stage_id=stage_id,
        )
        if not skip_verify:
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

        print(f"INFO: Rendering project {resolved_project.project_uuid} with draft {draft_uuid}")
        client.put_draft_preview_settings(
            draft_uuid=draft_uuid,
            format_uuid=format_uuid,
            project_uuid=resolved_project.project_uuid,
        )
        download_url = client.poll_draft_preview_url(
            draft_uuid=draft_uuid,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        document = client.download_url_bytes(download_url)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(document)
        info_path = output_path.with_suffix(output_path.suffix + ".json")
        info_path.write_text(
            json.dumps(
                {
                    "api_url": api_url,
                    "project_uuid": resolved_project.project_uuid,
                    "project_created_by_tool": resolved_project.created_by_tool,
                    "source_template_id": source_coordinates.full_id,
                    "staged_template_id": staged_coordinates.full_id,
                    "draft_uuid": draft_uuid,
                    "format_uuid": format_uuid,
                    "output": str(output_path),
                    "bytes": len(document),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"INFO: Wrote render metadata to {info_path}")
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
        seed = {**project_payload, **{k: v for k, v in payload.items() if k != "project"}}
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


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
