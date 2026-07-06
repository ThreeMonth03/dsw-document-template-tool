"""Shared helpers for invoking package module entrypoints from CI scripts."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

RENDER_PROJECT_MODULE = "dsw_document_template_tool.cli.render_project"
RENDER_REGRESSION_MODULE = "dsw_document_template_tool.cli.render_regression"
TRANSFORM_TEMPLATE_MODULE = "dsw_document_template_tool.cli.transform_template"
TRANSLATION_TREE_MODULE = "dsw_document_template_tool.cli.translation_tree"


def module_command(python: str | Path, module: str, *args: object) -> list[str]:
    """Return a subprocess command for a package module CLI."""

    return [str(python), "-m", module, *map(str, args)]


def package_env(repo_root: Path, base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment that exposes this src-layout package to Python."""

    env = dict(base if base is not None else os.environ)
    src_path = str(repo_root / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else f"{src_path}{os.pathsep}{existing}"
    return env
