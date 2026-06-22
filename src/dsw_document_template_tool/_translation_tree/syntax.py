"""Shared Jinja and HTML syntax patterns used by translation-tree tooling."""

from __future__ import annotations

import re

JINJA_COMMENT_OR_BLOCK_PATTERN = re.compile(r"\{#.*?#\}|\{%.*?%\}", re.DOTALL)
JINJA_EXPR_PATTERN = re.compile(r"\{\{\s*(?P<expr>.*?)\s*\}\}", re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
