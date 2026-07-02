"""Sphinx configuration for the DSW document-template tooling docs."""

from __future__ import annotations

project = "DSW Document Template Tool"
author = "DSW document-template maintainers"
copyright = "2026, DSW document-template maintainers"

extensions = ["myst_parser"]
source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = []

myst_heading_anchors = 3
