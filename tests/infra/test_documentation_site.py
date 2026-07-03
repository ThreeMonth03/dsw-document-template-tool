"""Tests for documentation structure and maintainer command affordances."""

from __future__ import annotations

from pathlib import Path


def test_sphinx_index_references_all_source_documents(repo_root: Path) -> None:
    """Every maintained docs page should be reachable from the Sphinx index."""

    docs_dir = repo_root / "docs"
    index_text = (docs_dir / "index.md").read_text(encoding="utf-8")
    source_pages = sorted(
        path.relative_to(docs_dir).with_suffix("").as_posix()
        for path in docs_dir.rglob("*")
        if path.suffix in {".md", ".rst"} and path.name != "index.md" and "_build" not in path.parts
    )

    missing = [page for page in source_pages if page not in index_text]
    assert missing == []


def test_command_reference_keeps_make_as_primary_interface(repo_root: Path) -> None:
    """The command guide should keep routine commands wrapped in Make targets."""

    command_reference = (repo_root / "docs" / "command-reference.md").read_text(
        encoding="utf-8",
    )

    assert "## Direct CLI Use" in command_reference
    assert "Prefer `make` for routine work" in command_reference
    assert "src/dsw_document_template_tool/cli/" in command_reference
    assert "make build-upstream-artifacts" in command_reference
    assert "make render-regression-ci-plan" in command_reference
    assert "If a direct command becomes common in daily work, wrap it in `make`" in (
        command_reference
    )
