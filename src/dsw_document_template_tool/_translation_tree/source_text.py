"""Source-text normalization, summaries, and stable key helpers."""

from __future__ import annotations

import html
import re

from .._template_transform.jinja_literals import (
    extract_translatable_jinja_block_literals as _extract_translatable_jinja_block_literals,
)
from .._template_transform.jinja_literals import (
    extract_translatable_jinja_literals as _extract_translatable_jinja_literals,
)
from .ids import hash_text
from .placeholders import jinja_expr_to_placeholder
from .syntax import HTML_TAG_PATTERN, JINJA_COMMENT_OR_BLOCK_PATTERN, JINJA_EXPR_PATTERN

HTML_BLOCK_END_PATTERN = re.compile(
    r"</(?:p|li|h[1-6]|dt|dd|th|td|caption)>|<br\s*/?>",
    re.IGNORECASE,
)
VISIBLE_TEXT_PATTERN = re.compile(r"[A-Za-z0-9]+")
CONNECTOR_ONLY_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
HARD_FRAGMENT_SENTENCES = {
    "available via:",
    "available with",
    "this data.",
    "this data are",
    "we will use.",
}
HARD_FRAGMENT_PREFIXES = (
    '" of this dataset',
    ", but decided ",
    ", legally",
    ", which",
    "and we will ",
    "but we won't ",
    'in order to "',
)
SENTENCE_TEXT_REPLACEMENTS = (
    (re.compile(r"\bbecauseit\b", re.IGNORECASE), "because it"),
    (re.compile(r"\blegaly\b", re.IGNORECASE), "legally"),
    (re.compile(r"\bdataare\b", re.IGNORECASE), "data are"),
    (re.compile(r"\bdatamay\b", re.IGNORECASE), "data may"),
    (re.compile(r"\busethe\b", re.IGNORECASE), "use the"),
    (re.compile(r"\buseonly\b", re.IGNORECASE), "use only"),
    (re.compile(r"\bwithfollowing\b", re.IGNORECASE), "with following"),
)


def build_wrapper_key(*, relative_path: str, source_text: str) -> str:
    visible_text = extract_visible_text(source_text)
    slug = slugify_text(visible_text)
    return f"{slug}-{hash_text(relative_path + '|' + source_text)[:10]}"


def build_unit_key(*, relative_path: str, wrapper_name: str, source_text: str) -> str:
    visible_text = extract_visible_text(source_text)
    slug = slugify_text(visible_text)
    return f"{slug}-{hash_text(relative_path + '|' + wrapper_name + '|' + source_text)[:10]}"


def build_folder_name(*, index: int, slug: str) -> str:
    return f"{index:04d}-{slug}"


def extract_visible_text(source_text: str) -> str:
    stripped = JINJA_EXPR_PATTERN.sub(_replace_expr_with_visible_literals, source_text)
    stripped = JINJA_COMMENT_OR_BLOCK_PATTERN.sub(_replace_block_with_visible_literals, stripped)
    stripped = HTML_TAG_PATTERN.sub(" ", stripped)
    stripped = html.unescape(stripped)
    words = VISIBLE_TEXT_PATTERN.findall(stripped)
    if not words:
        return "unit"
    return " ".join(words[:8])


def slugify_text(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unit"


def contains_translatable_text(source_text: str) -> bool:
    stripped = JINJA_EXPR_PATTERN.sub(_replace_expr_with_visible_literals, source_text)
    stripped = JINJA_COMMENT_OR_BLOCK_PATTERN.sub(_replace_block_with_visible_literals, stripped)
    stripped = HTML_TAG_PATTERN.sub(" ", stripped)
    stripped = html.unescape(stripped)
    return VISIBLE_TEXT_PATTERN.search(stripped) is not None


def is_unsafe_translation_unit_source(source_text: str) -> bool:
    """Return true when replacing the unit would drop executable Jinja code."""

    return contains_jinja_block_or_comment(source_text)


def contains_jinja_block_or_comment(source_text: str) -> bool:
    return "{%" in source_text


def is_connector_only_translation_unit(source_text: str) -> bool:
    sentence = extract_sentence_text(source_text)
    reduced_sentence = re.sub(r"\{[^}]+\}", " ", sentence)
    words = re.findall(r"[A-Za-z]+", reduced_sentence)
    if not words:
        return True
    return all(word.lower() in CONNECTOR_ONLY_WORDS for word in words)


def hard_fragment_sentence_message(source_text: str) -> str | None:
    sentence = extract_sentence_text(source_text).strip()
    lowered_sentence = sentence.lower()
    if lowered_sentence in HARD_FRAGMENT_SENTENCES or lowered_sentence.startswith(
        HARD_FRAGMENT_PREFIXES
    ):
        return (
            f"`{sentence}` is only a sentence fragment. Expand/export should keep "
            "the surrounding phrase and any placeholders in the same translation unit."
        )
    return None


def extract_sentence_text(source_text: str) -> str:
    with_placeholders = JINJA_EXPR_PATTERN.sub(
        lambda match: jinja_expr_to_placeholder(match.group("expr")),
        source_text,
    )
    without_control = JINJA_COMMENT_OR_BLOCK_PATTERN.sub(
        _replace_block_with_sentence_text,
        with_placeholders,
    )
    with_line_breaks = HTML_BLOCK_END_PATTERN.sub(". ", without_control)
    without_tags = HTML_TAG_PATTERN.sub(" ", with_line_breaks)
    sentence = html.unescape(without_tags)
    sentence = re.sub(r"\s+", " ", sentence).strip()
    sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
    sentence = re.sub(r"([,;:])(?=[^\s/])", r"\1 ", sentence)
    sentence = re.sub(r"\s+/\s*\.", "", sentence)
    sentence = re.sub(r"(?<![/.])\.{2,}", ".", sentence)
    sentence = re.sub(r"(?<![/.])([.!?])\.", r"\1", sentence)
    sentence = re.sub(r"\s+\.", ".", sentence)
    sentence = re.sub(r":\.$", ":", sentence)
    sentence = re.sub(r"^,\s+(available at\b)", r"\1", sentence, flags=re.IGNORECASE)
    sentence = sentence.strip()
    sentence = repair_sentence_text_glue(sentence)
    return sentence or "(no visible sentence)"


def repair_sentence_text_glue(sentence: str) -> str:
    repaired = sentence
    for pattern, replacement in SENTENCE_TEXT_REPLACEMENTS:
        repaired = pattern.sub(replacement, repaired)
    return repaired


def _replace_expr_with_visible_literals(match: re.Match[str]) -> str:
    return " ".join(_extract_translatable_jinja_literals(match.group("expr")))


def _replace_block_with_visible_literals(match: re.Match[str]) -> str:
    token_text = match.group(0)
    if token_text.startswith("{#"):
        return " "
    literals = _extract_translatable_jinja_block_literals(match.group(0)[2:-2])
    if literals:
        return " ".join(literals)
    return " "


def _replace_block_with_sentence_text(match: re.Match[str]) -> str:
    token_text = match.group(0)
    if token_text.startswith("{#"):
        return " "
    inner = token_text[2:-2].strip().strip("-").strip()
    literals = _extract_translatable_jinja_block_literals(inner)
    if literals:
        return " ".join(literals)
    keyword = inner.split(None, 1)[0] if inner else ""
    if keyword in {"elif", "else"}:
        return " / "
    return " "
