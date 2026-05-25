#!/usr/bin/env python3
"""Render one already-filled DSW project with a local document template."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

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
DEFAULT_TEMPLATE_DIR = "outputs/document-templates/translated-expanded/dsw-science-europe-1.30.0"
DEFAULT_PROJECT_REF = "workspace/projects/test-project.json"
DEFAULT_OUTPUT = "outputs/project-render/test-project.pdf"
PDF_FORMAT_UUID = "68c26e34-5e77-4e15-9bf7-06ff92582257"


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(
        description=("Render an existing filled DSW project with a local document template draft."),
    )
    parser.add_argument(
        "--project-uuid",
        default=os.environ.get("DSW_PROJECT_UUID"),
        help="Existing DSW project UUID. Defaults to DSW_PROJECT_UUID, then --project-ref.",
    )
    parser.add_argument(
        "--project-ref",
        default=os.environ.get("DSW_PROJECT_REF", DEFAULT_PROJECT_REF),
        help="JSON project reference file used when --project-uuid is omitted.",
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
    return parser


def main() -> None:
    """Render the selected project and exit non-zero on failures."""

    args = build_argument_parser().parse_args()
    try:
        output_path = render_project(
            project_uuid=_resolve_project_uuid(args.project_uuid, Path(args.project_ref)),
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
        )
    except Exception as exc:
        print(f"FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"SUCCESS: Wrote rendered project document to {output_path}")


def render_project(
    *,
    project_uuid: str,
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
) -> Path:
    """Upload a local template as a draft preview and render an existing project."""

    template_dir = template_dir.resolve()
    output_path = output_path.resolve()
    if not template_dir.is_dir():
        raise TemplateToolError(f"Template directory does not exist: {template_dir}")

    source_coordinates = read_local_template_coordinates(template_dir)
    client = DSWApiClient(api_url=api_url, verify_ssl=verify_ssl)
    staged_dir: Path | None = None
    try:
        if api_key:
            client.set_token(api_key)
        else:
            client.login(email=email, password=password)
        if client.token is None:
            raise TemplateToolError("Authentication did not produce a DSW bearer token.")

        user = client.get_current_user()
        print(f"INFO: Authenticated as {user.get('name') or user.get('email')}")

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
        document = client.download_url_bytes(download_url)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(document)
        info_path = output_path.with_suffix(output_path.suffix + ".json")
        info_path.write_text(
            json.dumps(
                {
                    "api_url": api_url,
                    "project_uuid": project_uuid,
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
        client.close()
        if staged_dir is not None:
            shutil.rmtree(staged_dir.parent, ignore_errors=True)


def _resolve_project_uuid(project_uuid: str | None, project_ref: Path) -> str:
    if project_uuid:
        return project_uuid
    if project_ref.is_file():
        payload = json.loads(project_ref.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            ref_uuid = payload.get("project_uuid") or payload.get("uuid")
            if isinstance(ref_uuid, str) and ref_uuid:
                return ref_uuid
    raise TemplateToolError(
        f"Set --project-uuid, DSW_PROJECT_UUID, or a valid project reference at {project_ref}."
    )


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
