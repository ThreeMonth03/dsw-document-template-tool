"""Tests for documentation structure and maintainer command affordances."""

from __future__ import annotations

import re
from pathlib import Path


def test_sphinx_index_references_all_source_documents(repo_root: Path) -> None:
    """Every published docs page should be reachable from the Sphinx index."""

    docs_dir = repo_root / "docs"
    index_text = (docs_dir / "index.md").read_text(encoding="utf-8")
    github_only_pages = {"README"}
    source_pages = sorted(
        path.relative_to(docs_dir).with_suffix("").as_posix()
        for path in docs_dir.rglob("*")
        if path.suffix in {".md", ".rst"} and path.name != "index.md" and "_build" not in path.parts
    )

    missing = [
        page for page in source_pages if page not in github_only_pages and page not in index_text
    ]
    assert missing == []


def test_command_reference_keeps_make_as_primary_interface(repo_root: Path) -> None:
    """The command guide should keep routine commands wrapped in Make targets."""

    command_reference = (repo_root / "docs" / "command-reference.md").read_text(
        encoding="utf-8",
    )
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    make_targets = set(re.findall(r"^([a-z][a-z0-9-]+):", makefile, flags=re.MULTILINE))

    assert "## Direct CLI Use" in command_reference
    assert "Prefer `make` for routine work" in command_reference
    assert "src/dsw_document_template_tool/cli/" in command_reference
    assert "pyproject.toml" in command_reference
    assert "dsw-template-transform" in command_reference
    assert "dsw-template-tree" in command_reference
    assert "make build-upstream-artifacts" in command_reference
    assert "make render-regression-ci-plan" in command_reference
    assert "make render-regression-ci-plan-dry-run" in command_reference
    assert "make download-clean-scaffold-artifacts" in command_reference
    assert "make sync-translation-version-branches" in command_reference
    assert "make check-translation-repository-docs" in command_reference
    assert "make validate-translation-config" in command_reference
    assert "check-translation-repository-docs" in make_targets
    assert "download-clean-scaffold-artifacts" in make_targets
    assert "render-regression-ci-plan-dry-run" in make_targets
    assert "sync-translation-version-branches" in make_targets
    assert "validate-translation-config" in make_targets
    assert "If a direct command becomes common in daily work, wrap it in `make`" in (
        command_reference
    )


def test_configuration_reference_covers_maintained_config_files(repo_root: Path) -> None:
    """The config guide should explain source configs and generated boundaries."""

    config_reference = (repo_root / "docs" / "configuration-reference.md").read_text(
        encoding="utf-8",
    )

    expected_references = (
        "config/dsw-compat.yml",
        "config/regression.ci.yml",
        "config/regression.preview.yml",
        "config/regression.document.yml",
        "config/ruff.toml",
        "pyproject.toml",
        ".github/workflows/headless_render_regression.yml",
        ".github/workflows/pages.yml",
        ".github/dsw/docker-compose.yml",
        "examples/github-actions/document_template_translation_sync.yml",
        "examples/translation-repository/",
        "translation-config.yml",
    )
    for reference in expected_references:
        assert reference in config_reference

    assert "Generated configs are ignored by git" in config_reference
    assert "make validate-translation-config" in config_reference


def test_translation_repository_templates_are_copy_ready(repo_root: Path) -> None:
    """Downstream translation docs templates should describe the branch model."""

    template_dir = repo_root / "examples" / "translation-repository"
    expected_files = (
        template_dir / ".gitignore",
        template_dir / "README.md",
        template_dir / "docs" / "README.md",
        template_dir / "docs" / "branch-policy.md",
        template_dir / "docs" / "maintenance-runbook.md",
        template_dir / "docs" / "security-and-permissions.md",
    )
    for path in expected_files:
        assert path.is_file(), path

    templates_doc = (repo_root / "docs" / "translation-repository-templates.md").read_text(
        encoding="utf-8"
    )
    branch_policy = (template_dir / "docs" / "branch-policy.md").read_text(
        encoding="utf-8",
    )
    maintenance_runbook = (template_dir / "docs" / "maintenance-runbook.md").read_text(
        encoding="utf-8"
    )
    security_policy = (template_dir / "docs" / "security-and-permissions.md").read_text(
        encoding="utf-8"
    )

    assert "examples/translation-repository/" in templates_doc
    assert "sync/v*" in branch_policy
    assert "publish/v*" in branch_policy
    assert "public" in branch_policy
    assert "private" in branch_policy
    assert "gh workflow run document_template_translation_sync.yml" in (maintenance_runbook)
    assert "GITHUB_TOKEN" in security_policy
