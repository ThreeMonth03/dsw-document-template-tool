"""Manifest helpers for translator-facing template trees."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from .models import TranslationTreeError

TREE_MANIFEST_PATH = Path(".translation-tree") / "manifest.json"
TREE_VERSION = 2


def load_tree_manifest(tree_dir: Path) -> dict:
    """Load one translation tree manifest or fail with a workflow-level error."""

    manifest_path = tree_dir / TREE_MANIFEST_PATH
    if not manifest_path.is_file():
        raise TranslationTreeError(f"Missing translation-tree manifest at {manifest_path}")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {manifest_path}: {exc}"
        ) from exc
