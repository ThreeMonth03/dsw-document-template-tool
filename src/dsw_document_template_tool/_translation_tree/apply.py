"""Apply translator-edited units back into expanded template source."""

from __future__ import annotations

import re

from .._template_transform.scanner import lex_source_tokens as _lex_source_tokens
from .html_structure import (
    INLINE_TRANSLATOR_TAGS,
    find_single_outer_element,
    find_single_outer_inline_element,
)
from .ids import hash_text
from .models import TREE_REFRESH_HINT, TranslationEntry, TranslationTreeError
from .placeholders import (
    materialize_translation_placeholders,
    validate_translation_placeholders,
)
from .syntax import HTML_TAG_PATTERN, JINJA_COMMENT_OR_BLOCK_PATTERN

INLINE_PLACEHOLDER_ELEMENT_PATTERN = re.compile(
    r"<(?P<tag>a|em|small|span|strong)\b[^>]*>"
    r".*?\{\{\s*(?P<expr>.*?)\s*\}\}.*?"
    r"</(?P=tag)>",
    re.DOTALL | re.IGNORECASE,
)


def apply_unit_translations(
    *,
    source_file: str,
    wrapper_body: str,
    wrapper_units: list[dict[str, str | int]],
    translations: dict[tuple[str, str], TranslationEntry],
) -> str:
    rebuilt_parts: list[str] = []
    cursor = 0
    sorted_units = sorted(
        wrapper_units,
        key=lambda unit: (
            int(unit["unit_start"]),
            int(unit["unit_end"]),
        ),
    )

    for unit in sorted_units:
        unit_start = unit["unit_start"]
        unit_end = unit["unit_end"]
        unit_key = unit["unit_key"]
        unit_source_hash = unit["unit_source_hash"]
        if not isinstance(unit_start, int) or not isinstance(unit_end, int):
            raise TranslationTreeError(
                f"Invalid unit offsets in translation-tree manifest for {source_file}"
            )
        if not isinstance(unit_key, str) or not isinstance(unit_source_hash, str):
            raise TranslationTreeError(
                f"Invalid unit metadata in translation-tree manifest for {source_file}"
            )
        if unit_start < cursor or unit_end > len(wrapper_body) or unit_start >= unit_end:
            raise TranslationTreeError(
                f"Invalid unit span for {source_file} ({unit_key}): {unit_start}:{unit_end}"
            )

        source_unit_text = wrapper_body[unit_start:unit_end]
        current_unit_hash = hash_text(source_unit_text)
        if current_unit_hash != unit_source_hash:
            raise TranslationTreeError(
                "Expanded source unit changed since the translation tree was exported for "
                f"{source_file} ({unit_key}). {TREE_REFRESH_HINT}"
            )

        rebuilt_parts.append(wrapper_body[cursor:unit_start])
        translation_entry = translations.get((source_file, unit_key))
        if translation_entry is not None and translation_entry.text.strip():
            translation_text = translation_entry.text
            validate_translation_placeholders(
                source_file=source_file,
                unit_key=unit_key,
                translation_document_path=translation_entry.document_path,
                source_text=source_unit_text,
                translation_text=translation_text,
            )
            translation_text = materialize_translation_placeholders(
                source_text=source_unit_text,
                translation_text=translation_text,
            )
            translation_text = _preserve_single_outer_element(
                source_text=source_unit_text,
                translation_text=translation_text,
            )
        else:
            translation_text = source_unit_text
        rebuilt_parts.append(translation_text)
        cursor = unit_end

    rebuilt_parts.append(wrapper_body[cursor:])
    return "".join(rebuilt_parts)


def _preserve_single_outer_element(*, source_text: str, translation_text: str) -> str:
    """Keep simple structural tags when translators provide text-only content."""

    if HTML_TAG_PATTERN.search(translation_text):
        return translation_text

    tokens = _lex_source_tokens(source_text)
    outer_element = find_single_outer_element(tokens=tokens)
    if outer_element is None:
        outer_element = find_single_outer_inline_element(tokens=tokens)
    outer_tag = outer_element[0] if outer_element is not None else ""
    if outer_tag not in INLINE_TRANSLATOR_TAGS:
        translation_text = _preserve_inline_placeholder_elements(
            source_text=source_text,
            translation_text=translation_text,
        )
        translation_text = _preserve_single_inner_inline_element(
            source_text=source_text,
            translation_text=translation_text,
        )

    if outer_element is None:
        return translation_text

    _, inner_start, inner_end = outer_element
    return source_text[:inner_start] + translation_text + source_text[inner_end:]


def _preserve_single_inner_inline_element(*, source_text: str, translation_text: str) -> str:
    """Keep a single inline child such as ``<p><em>...</em></p>`` intact."""

    tokens = _lex_source_tokens(source_text)
    outer_element = find_single_outer_element(tokens=tokens)
    if outer_element is None:
        return translation_text

    _, inner_start, inner_end = outer_element
    inner_source = source_text[inner_start:inner_end]
    inner_tokens = _lex_source_tokens(inner_source)
    inner_element = find_single_outer_inline_element(tokens=inner_tokens)
    if inner_element is None:
        return translation_text

    _, inline_inner_start, inline_inner_end = inner_element
    if _contains_jinja_block_or_comment(inner_source):
        return translation_text

    return inner_source[:inline_inner_start] + translation_text + inner_source[inline_inner_end:]


def _preserve_inline_placeholder_elements(*, source_text: str, translation_text: str) -> str:
    """Restore inline source markup that only wraps one visible placeholder.

    Translators usually should not edit HTML. When they provide text-only
    translations, source links such as ``<a href="{{ pid }}">{{ pid }}</a>``
    still need to survive because the href is machine wiring, not prose.
    """

    restored_text = translation_text
    for match in INLINE_PLACEHOLDER_ELEMENT_PATTERN.finditer(source_text):
        inline_source = match.group(0)
        if _contains_jinja_block_or_comment(inline_source):
            continue

        expression = " ".join(match.group("expr").strip().split())
        visible_inner = HTML_TAG_PATTERN.sub("", inline_source)
        visible_inner = re.sub(r"\s+", " ", visible_inner).strip()
        if visible_inner != "{{ " + expression + " }}":
            continue

        placeholder = "{{ " + expression + " }}"
        restored_text = restored_text.replace(placeholder, inline_source, 1)
    return restored_text


def _contains_jinja_block_or_comment(source_text: str) -> bool:
    return JINJA_COMMENT_OR_BLOCK_PATTERN.search(source_text) is not None
