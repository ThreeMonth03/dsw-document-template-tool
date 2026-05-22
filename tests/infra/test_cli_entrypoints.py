"""Smoke tests for repository CLI entrypoints."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_render_regression_help(repo_root) -> None:
    """The main regression CLI should expose a working help screen."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "render_regression.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "headless DSW template regression" in result.stdout
    assert "--config" in result.stdout


def test_transform_template_help(repo_root) -> None:
    """The transform CLI should expose its subcommands."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "transform_template.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Expand or compact DSW document templates" in result.stdout
    assert "expand" in result.stdout
    assert "compact" in result.stdout


def test_translation_tree_help(repo_root) -> None:
    """The translation-tree CLI should expose export/sync commands."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "translation_tree.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "translator-facing trees" in result.stdout
    assert "export" in result.stdout
    assert "sync" in result.stdout


def test_checked_in_compact_and_expanded_templates_verify(repo_root: Path) -> None:
    """Both checked-in template forms should be accepted by dsw-tdk."""

    executable = Path(sys.executable).with_name("dsw-tdk")
    template_dirs = [
        repo_root / "workspace" / "document-templates" / "compact" / "dsw-science-europe-1.30.0",
        repo_root / "workspace" / "document-templates" / "expanded" / "dsw-science-europe-1.30.0",
    ]

    for template_dir in template_dirs:
        result = subprocess.run(
            [str(executable), "verify", str(template_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "SUCCESS: The template is valid!" in result.stdout
