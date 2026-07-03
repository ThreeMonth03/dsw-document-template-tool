"""Sphinx configuration for the DSW document-template tooling docs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

project = "DSW Document Template Tool"
author = "DSW document-template maintainers"
copyright = "2026, DSW document-template maintainers"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]
source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "DSW Document Template Tool"
html_static_path: list[str] = []

autodoc_class_signature = "separated"
autodoc_default_options = {
    "exclude-members": "__init__",
}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"

myst_enable_extensions = [
    "colon_fence",
]
myst_heading_anchors = 3
napoleon_google_docstring = True
napoleon_numpy_docstring = False
