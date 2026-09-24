"""The isolated CI storage stack must not depend on vanished/floating images."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def test_ci_minio_defaults_use_pinned_official_quay_images(repo_root: Path) -> None:
    """Keep both version overrides, but require immutable default image digests."""

    compose = yaml.safe_load((repo_root / ".github/dsw/docker-compose.yml").read_text())
    for service, repository, variable in (
        ("minio", "minio", "MINIO_VERSION"),
        ("minio-init", "mc", "MINIO_MC_VERSION"),
    ):
        image = compose["services"][service]["image"]
        prefix = f"quay.io/minio/{repository}:${{{variable}:-"
        assert image.startswith(prefix)
        default = image.removeprefix(prefix).removesuffix("}")
        assert re.fullmatch(
            r"RELEASE\.\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z@sha256:[0-9a-f]{64}",
            default,
        )
        assert "latest" not in image


def test_ci_storage_remains_ephemeral_and_server_version_is_unchanged(
    repo_root: Path,
) -> None:
    """This repair must not migrate production data or silently upgrade MinIO."""

    compose = yaml.safe_load((repo_root / ".github/dsw/docker-compose.yml").read_text())
    assert "RELEASE.2025-05-24T17-08-30Z@" in compose["services"]["minio"]["image"]
    assert "volumes" not in compose["services"]["minio"]
    assert "volumes" not in compose
