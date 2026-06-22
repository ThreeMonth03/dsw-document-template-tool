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


def test_render_project_help(repo_root) -> None:
    """The project render CLI should expose a working help screen."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "render_project.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "existing or fixture DSW project" in result.stdout
    assert "--project-uuid" in result.stdout
    assert "--keep-created-project" in result.stdout


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
    """The translation-tree CLI should expose export/audit/sync commands."""

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "translation_tree.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "translator-facing trees" in result.stdout
    assert "export" in result.stdout
    assert "audit" in result.stdout
    assert "audit-output" in result.stdout
    assert "sync" in result.stdout
    assert "merge" in result.stdout

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "translation_tree.py"), "sync", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--template-id" in result.stdout

    result = subprocess.run(
        [sys.executable, str(repo_root / "src" / "translation_tree.py"), "audit", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--tree" in result.stdout
    assert "--source" in result.stdout

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "src" / "translation_tree.py"),
            "audit-output",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--source" in result.stdout
    assert "--output" in result.stdout

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "src" / "translation_tree.py"),
            "merge",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--old-tree" in result.stdout
    assert "--new-tree" in result.stdout
    assert "--output" in result.stdout
    assert "--source-lang" in result.stdout
    assert "--target-lang" in result.stdout
    assert "--allow-sentence-matches" in result.stdout


def test_resolve_upstream_refs_expands_version_ranges(repo_root: Path) -> None:
    """The CI helper should resolve semantic version ranges from an upstream remote."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_upstream_refs.py"),
            "--remote",
            "https://github.com/ds-wizard/science-europe-template.git",
            "latest",
            "v1.30.0+",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    refs = result.stdout.strip().split()
    assert refs[0] == "latest"
    assert "v1.30.0" in refs
    assert "v1.30.1" in refs
    assert "v1.29.1" not in refs


def test_resolve_upstream_refs_expands_compatibility_ranges(repo_root: Path) -> None:
    """The older compatibility smoke range should include all tags since v1.21.0."""

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_upstream_refs.py"),
            "--remote",
            "https://github.com/ds-wizard/science-europe-template.git",
            "v1.21.0+",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    refs = result.stdout.strip().split()
    assert refs[0] == "v1.21.0"
    assert "v1.30.1" in refs
    assert "v1.20.0" not in refs


def test_dsw_tdk_verify_command_is_available() -> None:
    """The dsw-tdk verify command should be installed for Makefile targets."""

    executable = Path(sys.executable).with_name("dsw-tdk")
    result = subprocess.run(
        [str(executable), "verify", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Usage: dsw-tdk verify" in result.stdout
