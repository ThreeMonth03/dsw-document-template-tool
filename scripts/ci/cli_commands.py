"""Shared helpers for invoking installed package CLI commands from CI scripts."""

from __future__ import annotations

from pathlib import Path

RENDER_PROJECT_COMMAND = "dsw-template-render-project"
RENDER_REGRESSION_COMMAND = "dsw-template-render-regression"
TRANSFORM_TEMPLATE_COMMAND = "dsw-template-transform"
TRANSLATION_TREE_COMMAND = "dsw-template-tree"


def tool_command(tooling_root: Path, command: str, *args: object) -> list[str]:
    """Return a subprocess command for an installed tooling CLI."""

    return [str(tooling_root / ".venv" / "bin" / command), *map(str, args)]
