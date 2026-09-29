"""The isolated CI storage stack must not depend on vanished/floating images."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def test_ci_minio_builds_pinned_official_release_assets(repo_root: Path) -> None:
    """Build verified upstream binaries without depending on MinIO registries."""

    compose = yaml.safe_load((repo_root / ".github/dsw/docker-compose.yml").read_text())
    for service, target in (
        ("minio", "minio"),
        ("minio-init", "mc"),
    ):
        settings = compose["services"][service]
        assert settings["image"].startswith(f"dsw-ci-{target}:RELEASE.")
        assert settings["platform"] == "linux/amd64"
        assert settings["pull_policy"] == "build"
        assert settings["build"] == {"context": "./storage", "target": target}

    dockerfile = (repo_root / ".github/dsw/storage/Dockerfile").read_text()
    assert re.search(
        r"^FROM debian:bookworm-slim@sha256:[0-9a-f]{64} AS base$",
        dockerfile,
        re.MULTILINE,
    )
    assert (
        len(re.findall(r"^ADD .*--checksum=sha256:[0-9a-f]{64}\s", dockerfile, re.MULTILINE)) == 2
    )
    for project in ("minio", "mc"):
        assert f"https://github.com/minio/{project}/releases/download/RELEASE." in dockerfile


def test_ci_storage_remains_ephemeral_and_server_version_is_unchanged(
    repo_root: Path,
) -> None:
    """This repair must not migrate production data or silently upgrade MinIO."""

    compose = yaml.safe_load((repo_root / ".github/dsw/docker-compose.yml").read_text())
    assert compose["services"]["minio"]["image"] == "dsw-ci-minio:RELEASE.2025-05-24T17-08-30Z"
    assert "volumes" not in compose["services"]["minio"]
    assert "volumes" not in compose
