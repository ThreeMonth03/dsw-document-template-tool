#!/usr/bin/env python3
"""Command-line adapter for rendering one DSW project."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dsw_document_template_tool.render_project import render_project

DEFAULT_API_URL = "http://localhost:3000/wizard-api"
DEFAULT_EMAIL = "albert.einstein@example.com"
DEFAULT_OUTPUT = "outputs/project-render/dsw-science-europe/v1.30.0/zh-Hant/test-project.pdf"
DEFAULT_PASSWORD = "password"
DEFAULT_PROJECT_REF = "fixtures/projects/demo/test-project.json"
DEFAULT_TDK_EXECUTABLE = ".venv/bin/dsw-tdk"
DEFAULT_TEMPLATE_DIR = (
    "outputs/document-templates/dsw-science-europe/v1.30.0/zh-Hant/"
    "dsw-science-europe-zh-hant-1.30.0"
)
PDF_FORMAT_UUID = "68c26e34-5e77-4e15-9bf7-06ff92582257"


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the render-project command parser."""

    parser = argparse.ArgumentParser(
        description="Render an existing or fixture DSW project with a document template.",
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
            "JSON project reference used when --project-uuid is omitted. It may point at "
            "an existing project UUID or define a KM/events recipe."
        ),
    )
    parser.add_argument(
        "--template-dir",
        default=os.environ.get("DSW_TEMPLATE_DIR", DEFAULT_TEMPLATE_DIR),
        help="Local document template directory to upload as a draft.",
    )
    parser.add_argument(
        "--template-package",
        default=os.environ.get("DSW_TEMPLATE_PACKAGE"),
        help=(
            "Released template package zip to import before rendering. When set, "
            "--template-dir and draft preview upload are not used."
        ),
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
        "--verify-ssl",
        action="store_true",
        default=_env_bool("DSW_VERIFY_SSL", default=False),
        help="Verify TLS certificates for DSW API requests.",
    )
    parser.add_argument(
        "--keep-created-project",
        action="store_true",
        default=_env_bool("DSW_KEEP_CREATED_PROJECT", default=False),
        help="Keep a project created from --project-ref after rendering.",
    )
    return parser


def main() -> None:
    """Render the selected project and exit non-zero on failure."""

    args = build_argument_parser().parse_args()
    try:
        output_path = render_project(
            project_uuid=args.project_uuid,
            project_ref=Path(args.project_ref),
            template_dir=Path(args.template_dir),
            template_package=Path(args.template_package) if args.template_package else None,
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
            verify_ssl=args.verify_ssl,
            keep_created_project=args.keep_created_project,
        )
    except Exception as exc:
        print(f"FAILURE: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"SUCCESS: Wrote rendered project document to {output_path}")


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
