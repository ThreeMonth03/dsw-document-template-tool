"""Visible-text helpers for translation template transforms."""

from __future__ import annotations

import html
import re

from .jinja_literals import (
    extract_translatable_jinja_block_literals,
    extract_translatable_jinja_literals,
)
from .markers import GENERATED_BLOCK_PATTERN, generated_block_body
from .scanner import (
    HTML_TAG_PATTERN,
    JINJA_BLOCK_PATTERN,
    JINJA_EXPR_PATTERN,
    VISIBLE_TEXT_PATTERN,
)


def visible_text_for_rewrite(source_text: str) -> str:
    """Return normalized visible text used by sentence-rewrite heuristics."""

    stripped = JINJA_EXPR_PATTERN.sub(" {value} ", source_text)
    stripped = JINJA_BLOCK_PATTERN.sub(" ", stripped)
    stripped = re.sub(r"\{#.*?#\}", " ", stripped, flags=re.DOTALL)
    stripped = HTML_TAG_PATTERN.sub(" ", stripped)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def visible_words(source_text: str) -> list[str]:
    """Return ASCII-ish visible words for conservative rewrite heuristics."""

    return re.findall(r"[A-Za-z0-9]+", visible_text_for_rewrite(source_text))


def contains_translatable_text(source_text: str) -> bool:
    """Return whether one HTML/Jinja region contains translator-facing text."""

    stripped = GENERATED_BLOCK_PATTERN.sub(lambda match: generated_block_body(match), source_text)
    stripped = JINJA_EXPR_PATTERN.sub(_replace_expr_with_visible_literals, stripped)
    stripped = JINJA_BLOCK_PATTERN.sub(_replace_block_with_visible_literals, stripped)
    stripped = re.sub(r"\{#.*?#\}", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"\{%.*?%\}", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"\{\{.*?\}\}", "", stripped, flags=re.DOTALL)
    visible_text = html.unescape(HTML_TAG_PATTERN.sub("", stripped))
    return VISIBLE_TEXT_PATTERN.search(visible_text) is not None


def is_translatable_jinja_block(token_text: str) -> bool:
    """Return whether a Jinja block token contains translatable string literals."""

    match = JINJA_BLOCK_PATTERN.fullmatch(token_text)
    return bool(match and extract_translatable_jinja_block_literals(match.group("body")))


def _replace_expr_with_visible_literals(match: re.Match[str]) -> str:
    return " ".join(extract_translatable_jinja_literals(match.group("expr")))


def _replace_block_with_visible_literals(match: re.Match[str]) -> str:
    return " ".join(extract_translatable_jinja_block_literals(match.group("body")))
