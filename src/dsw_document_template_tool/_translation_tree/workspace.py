"""Workspace validation helpers for expanded document templates."""

from __future__ import annotations

from pathlib import Path

from .._template_transform.workspace import MANIFEST_PATH
from .models import TranslationTreeError


def validate_expanded_workspace(source_dir: Path) -> None:
    """Raise when a directory is not an expanded template workspace."""

    if not (source_dir / MANIFEST_PATH).is_file():
        raise TranslationTreeError(
            f"{source_dir} is not an expanded template workspace; missing {MANIFEST_PATH}"
        )
