"""Filesystem helpers for translation-tree workflows."""

from __future__ import annotations

import shutil
from pathlib import Path


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
