"""HTML token helpers shared by extraction and translation application."""

from __future__ import annotations

from ..template_transform import (
    ANNOTATABLE_HTML_TAGS,
    SourceToken,
    _find_matching_tag_end,
)

INLINE_TRANSLATOR_TAGS = {"a", "em", "small", "span", "strong"}


def find_single_outer_element_inner_bounds(
    *,
    tokens: list[SourceToken],
) -> tuple[int, int] | None:
    element = find_single_outer_element(tokens=tokens)
    if element is None:
        return None
    return (element[1], element[2])


def find_single_outer_element(
    *,
    tokens: list[SourceToken],
) -> tuple[str, int, int] | None:
    first_index = find_first_meaningful_token_index(tokens)
    if first_index is None:
        return None

    first_token = tokens[first_index]
    if (
        first_token.kind != "html_tag"
        or not first_token.is_opening_tag
        or first_token.is_self_closing_tag
        or first_token.tag_name not in ANNOTATABLE_HTML_TAGS
    ):
        return None

    end_index = _find_matching_tag_end(tokens=tokens, start_index=first_index)
    if end_index is None:
        return None

    end_token = tokens[end_index]
    if (
        end_token.kind != "html_tag"
        or not end_token.is_closing_tag
        or end_token.tag_name != first_token.tag_name
    ):
        return None

    if any(not is_ignorable_outer_token(token) for token in tokens[:first_index]):
        return None
    if any(not is_ignorable_outer_token(token) for token in tokens[end_index + 1 :]):
        return None

    return (first_token.tag_name or "", first_token.end, end_token.start)


def find_single_outer_inline_element(
    *,
    tokens: list[SourceToken],
) -> tuple[str, int, int] | None:
    first_index = find_first_meaningful_token_index(tokens)
    if first_index is None:
        return None

    first_token = tokens[first_index]
    if (
        first_token.kind != "html_tag"
        or not first_token.is_opening_tag
        or first_token.is_self_closing_tag
        or first_token.tag_name not in INLINE_TRANSLATOR_TAGS
    ):
        return None

    end_index = _find_matching_tag_end(tokens=tokens, start_index=first_index)
    if end_index is None:
        return None

    end_token = tokens[end_index]
    if (
        end_token.kind != "html_tag"
        or not end_token.is_closing_tag
        or end_token.tag_name != first_token.tag_name
    ):
        return None

    if any(not is_ignorable_outer_token(token) for token in tokens[:first_index]):
        return None
    if any(not is_ignorable_outer_token(token) for token in tokens[end_index + 1 :]):
        return None

    return (first_token.tag_name or "", first_token.end, end_token.start)


def find_first_meaningful_token_index(tokens: list[SourceToken]) -> int | None:
    for index, token in enumerate(tokens):
        if not is_ignorable_outer_token(token):
            return index
    return None


def is_ignorable_outer_token(token: SourceToken) -> bool:
    if token.kind == "jinja_comment":
        return True
    if token.kind == "text" and not token.text.strip():
        return True
    return False
