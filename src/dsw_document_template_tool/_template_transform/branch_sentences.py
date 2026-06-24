"""Reversible rewrites for branch-built sentence fragments."""

from __future__ import annotations

import re

from .branch_groups import (
    BranchRewriteGroup,
)
from .branch_groups import (
    active_jinja_if_conditions_at as _active_jinja_if_conditions_at,
)
from .branch_groups import (
    collect_top_level_branch_rewrite_groups as _collect_top_level_branch_rewrite_groups,
)
from .branch_groups import (
    collect_top_level_optional_rewrite_groups as _collect_top_level_optional_rewrite_groups,
)
from .jinja_blocks import (
    jinja_block_inner as _jinja_block_inner,
)
from .jinja_blocks import (
    jinja_block_keyword as _jinja_block_keyword,
)
from .jinja_blocks import (
    jinja_block_trims_following_whitespace as _jinja_block_trims_following_whitespace,
)
from .jinja_blocks import (
    jinja_block_trims_previous_whitespace as _jinja_block_trims_previous_whitespace,
)
from .markers import decode_marker_payload, encode_marker_payload
from .models import TemplateTransformError
from .scanner import (
    ANNOTATABLE_HTML_TAGS,
)
from .scanner import (
    find_matching_tag_end as _find_matching_tag_end,
)
from .scanner import (
    lex_source_tokens as _lex_source_tokens,
)
from .text_visibility import (
    contains_translatable_text as _contains_translatable_text,
)
from .text_visibility import (
    visible_text_for_rewrite as _visible_text_for_rewrite,
)
from .text_visibility import (
    visible_words as _visible_words,
)

BRANCH_SENTENCE_REWRITE_PATTERN = re.compile(
    r"\{# __tr_branch_sentence_original:(?P<payload>[A-Za-z0-9_-]+=*) #\}"
    r".*?"
    r"\{# __tr_branch_sentence_original:end #\}",
    re.DOTALL,
)


def rewrite_common_prefix_branch_sentences(source_text: str) -> str:
    """Duplicate shared sentence parts into simple mutually exclusive branches."""

    tokens = _lex_source_tokens(source_text)
    rewrite_regions: list[tuple[int, int, str]] = []

    for start_index, token in enumerate(tokens):
        if (
            token.kind != "html_tag"
            or not token.is_opening_tag
            or token.is_self_closing_tag
            or token.tag_name not in ANNOTATABLE_HTML_TAGS
        ):
            continue
        end_index = _find_matching_tag_end(tokens=tokens, start_index=start_index)
        if end_index is None:
            continue
        end_token = tokens[end_index]
        if (
            end_token.kind != "html_tag"
            or not end_token.is_closing_tag
            or end_token.tag_name != token.tag_name
        ):
            continue

        inner_start = token.end
        inner_end = end_token.start
        inner_text = source_text[inner_start:inner_end]
        active_conditions = _active_jinja_if_conditions_at(tokens=tokens, token_index=start_index)
        rewritten_inner = _rewrite_inner_common_prefix_branch(
            inner_text,
            opening_tag=token.text,
            closing_tag=end_token.text,
            active_conditions=active_conditions,
        )
        if rewritten_inner is None:
            continue

        original_region = source_text[token.start : end_token.end]
        encoded_original = encode_marker_payload(original_region)
        rewritten_region = (
            f"{{# __tr_branch_sentence_original:{encoded_original} #}}"
            f"{rewritten_inner}"
            "{# __tr_branch_sentence_original:end #}"
        )
        rewrite_regions.append((token.start, end_token.end, rewritten_region))

    if not rewrite_regions:
        return source_text
    return _replace_non_overlapping_regions(source_text, rewrite_regions)


def restore_branch_sentence_rewrites(source_text: str) -> str:
    """Restore original common-prefix branches when compacting."""

    def replace(match: re.Match[str]) -> str:
        try:
            return decode_marker_payload(match.group("payload"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise TemplateTransformError("Invalid branch sentence rewrite marker") from exc

    return BRANCH_SENTENCE_REWRITE_PATTERN.sub(replace, source_text)


def _rewrite_inner_common_prefix_branch(
    inner_text: str,
    *,
    opening_tag: str,
    closing_tag: str,
    active_conditions: list[str],
) -> str | None:
    inner_tokens = _lex_source_tokens(inner_text)
    groups = _collect_top_level_branch_rewrite_groups(tokens=inner_tokens)
    if len(groups) == 1:
        rewritten_group = _rewrite_single_alternative_branch_group(
            inner_text=inner_text,
            opening_tag=opening_tag,
            closing_tag=closing_tag,
            group=groups[0],
            active_conditions=active_conditions,
        )
        if rewritten_group is not None:
            return rewritten_group

    optional_groups = _collect_top_level_optional_rewrite_groups(tokens=inner_tokens)
    if len(optional_groups) == 1:
        rewritten_group = _rewrite_single_alternative_branch_group(
            inner_text=inner_text,
            opening_tag=opening_tag,
            closing_tag=closing_tag,
            group=optional_groups[0],
            active_conditions=active_conditions,
        )
        if rewritten_group is not None:
            return rewritten_group

    rewritten_single_choice = _rewrite_single_choice_optional_branch_groups(
        inner_text=inner_text,
        opening_tag=opening_tag,
        closing_tag=closing_tag,
        active_conditions=active_conditions,
    )
    if rewritten_single_choice is not None:
        return rewritten_single_choice

    rewritten_nested_fragments = _rewrite_nested_common_prefix_branch_fragments(inner_text)
    if rewritten_nested_fragments is not None:
        return f"{opening_tag}{rewritten_nested_fragments}{closing_tag}"

    return None


def _rewrite_nested_common_prefix_branch_fragments(inner_text: str) -> str | None:
    """Rewrite nested branch fragments inside a larger sentence-preserving element.

    Some templates have a paragraph-level optional fragment followed by a nested
    if/elif reason, for example `available with {% if reason %}...`.  The outer
    paragraph cannot be fully expanded without a Cartesian explosion, but the
    nested branch can still duplicate its immediate visible prefix so translators
    do not receive `available with` or `because ...` as disconnected units.
    """

    rewritten = _rewrite_common_prefix_branch_fragments(inner_text)
    if rewritten == inner_text:
        return None
    return rewritten


def _rewrite_common_prefix_branch_fragments(source_text: str) -> str:
    tokens = _lex_source_tokens(source_text)
    groups = _collect_top_level_branch_rewrite_groups(tokens=tokens)
    if len(groups) == 1:
        rewritten = _rewrite_single_alternative_branch_fragment(
            source_text=source_text,
            group=groups[0],
        )
        if rewritten is not None:
            return rewritten

    replacements: list[tuple[int, int, str]] = []
    for group in _collect_top_level_optional_rewrite_groups(tokens=tokens):
        for branch in group.branches:
            branch_text = source_text[branch.start : branch.end]
            rewritten_branch = _rewrite_common_prefix_branch_fragments(branch_text)
            if rewritten_branch != branch_text:
                replacements.append((branch.start, branch.end, rewritten_branch))

    if not replacements:
        return source_text
    return _replace_non_overlapping_regions(source_text, replacements)


def _rewrite_single_alternative_branch_fragment(
    *,
    source_text: str,
    group: BranchRewriteGroup,
) -> str | None:
    """Rewrite one nested if/elif/else group without adding HTML wrappers."""

    prefix = source_text[: group.start]
    suffix = source_text[group.end :]
    setup_prefix, visible_prefix = _split_rewrite_setup_blocks(prefix)
    prefix_has_text = _contains_translatable_text(prefix)
    suffix_has_words = bool(_visible_words(suffix))
    if _contains_rewrite_unsafe_tail_control(suffix):
        return None
    if not prefix_has_text and not suffix_has_words:
        return None
    if prefix_has_text and _visible_text_for_rewrite(prefix).rstrip().endswith(
        (".", "!", "?", ";")
    ):
        return None
    if not all(
        _is_simple_branch_sentence_fragment(source_text[branch.start : branch.end])
        for branch in group.branches
    ):
        return None

    suffix_after_group = (
        suffix.lstrip() if _jinja_block_trims_following_whitespace(group.end_text) else suffix
    )
    rewritten_parts: list[str] = [setup_prefix]
    for branch in group.branches:
        branch_body = source_text[branch.start : branch.end]
        if _jinja_block_trims_following_whitespace(branch.opener_text):
            branch_body = branch_body.lstrip()
        if branch.rstrip_body:
            branch_body = branch_body.rstrip()
        branch_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=branch_body,
            opener_text=branch.opener_text,
        )
        rewritten_parts.append(branch.opener_text)
        rewritten_parts.append(branch_prefix)
        rewritten_parts.append(branch_body)
        rewritten_parts.append(suffix_after_group)
    if not any(_jinja_block_keyword(branch.opener_text) == "else" for branch in group.branches):
        fallback_opener = group.branches[0].opener_text
        fallback_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=suffix_after_group,
            opener_text=fallback_opener,
        )
        rewritten_parts.append("{% else %}")
        rewritten_parts.append(fallback_prefix)
        rewritten_parts.append(suffix_after_group)
    rewritten_parts.append(group.end_text)
    return "".join(rewritten_parts)


def _rewrite_single_alternative_branch_group(
    *,
    inner_text: str,
    opening_tag: str,
    closing_tag: str,
    group: BranchRewriteGroup,
    active_conditions: list[str],
) -> str | None:
    """Rewrite one if/elif/else group into complete branch sentences."""

    prefix = inner_text[: group.start]
    suffix = inner_text[group.end :]
    setup_prefix, visible_prefix = _split_rewrite_setup_blocks(prefix)
    prefix_has_text = _contains_translatable_text(prefix)
    suffix_has_words = bool(_visible_words(suffix))
    if _contains_rewrite_unsafe_tail_control(suffix):
        return None
    if not prefix_has_text and not suffix_has_words:
        return None
    if prefix_has_text and _visible_text_for_rewrite(prefix).rstrip().endswith(
        (".", "!", "?", ";")
    ):
        return None
    if not all(
        _is_simple_branch_sentence_fragment(inner_text[branch.start : branch.end])
        for branch in group.branches
    ):
        return None

    suffix_after_group = (
        suffix.lstrip() if _jinja_block_trims_following_whitespace(group.end_text) else suffix
    )
    rewritten_parts: list[str] = []
    rewritten_parts.append(setup_prefix)
    for branch in group.branches:
        branch_body = inner_text[branch.start : branch.end]
        if _jinja_block_trims_following_whitespace(branch.opener_text):
            branch_body = branch_body.lstrip()
        if branch.rstrip_body:
            branch_body = branch_body.rstrip()
        branch_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=branch_body,
            opener_text=branch.opener_text,
        )
        rewritten_parts.append(branch.opener_text)
        rewritten_parts.append(opening_tag)
        rewritten_parts.append(branch_prefix)
        rewritten_parts.append(branch_body)
        rewritten_parts.append(suffix_after_group)
        rewritten_parts.append(closing_tag)
    has_explicit_else = any(
        _jinja_block_keyword(branch.opener_text) == "else" for branch in group.branches
    )
    if not has_explicit_else and not _active_truthy_selector_covers_group(
        group=group,
        active_conditions=active_conditions,
    ):
        fallback_opener = group.branches[0].opener_text
        fallback_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=suffix_after_group,
            opener_text=fallback_opener,
        )
        rewritten_parts.append("{% else %}")
        rewritten_parts.append(opening_tag)
        rewritten_parts.append(fallback_prefix)
        rewritten_parts.append(suffix_after_group)
        rewritten_parts.append(closing_tag)
    rewritten_parts.append(group.end_text)
    return "".join(rewritten_parts)


def _active_truthy_selector_covers_group(
    *,
    group: BranchRewriteGroup,
    active_conditions: list[str],
) -> bool:
    """Avoid exposing unreachable enum fallbacks as translator-facing fragments.

    DSW answer branches often look like:

    `{% if answer %}<p>Prefix {% if answer == option_a %}...{% endif %}</p>{% endif %}`.

    The generic rewriter normally adds an `else` fallback to preserve arbitrary
    unknown selector values. For enumerated DSW answers, that fallback renders
    only the prefix (`We will use.`), which is not useful to translate.  If an
    outer condition already checks the same selector for truthiness, we treat the
    inner equality branches as the intended closed option set.
    """

    selector_name = _branch_group_equality_selector_name(group)
    if selector_name is None:
        return False
    return selector_name in {
        _normalize_truthy_condition(condition) for condition in active_conditions
    }


def _branch_group_equality_selector_name(group: BranchRewriteGroup) -> str | None:
    selector_names: set[str] = set()
    for branch in group.branches:
        keyword = _jinja_block_keyword(branch.opener_text)
        if keyword == "else":
            return None
        if keyword not in {"if", "elif"}:
            continue
        condition = _jinja_block_inner(branch.opener_text).split(None, 1)
        if len(condition) != 2:
            return None
        match = re.match(
            r"(?P<selector>[A-Za-z_][A-Za-z0-9_.]*)\s*==\s*.+\Z",
            condition[1],
            flags=re.DOTALL,
        )
        if match is None:
            return None
        selector_names.add(match.group("selector"))
    if len(selector_names) != 1:
        return None
    return next(iter(selector_names))


def _normalize_truthy_condition(condition: str) -> str:
    normalized = condition.strip()
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", normalized):
        return normalized
    return ""


def _rewrite_single_choice_optional_branch_groups(
    *,
    inner_text: str,
    opening_tag: str,
    closing_tag: str,
    active_conditions: list[str],
) -> str | None:
    """Rewrite adjacent optional if fragments when an outer condition guarantees one choice."""

    if not _is_single_choice_context(active_conditions):
        return None

    inner_tokens = _lex_source_tokens(inner_text)
    groups = _collect_top_level_optional_rewrite_groups(tokens=inner_tokens)
    if len(groups) < 2:
        return None
    if not all(len(group.branches) == 1 for group in groups):
        return None

    prefix = inner_text[: groups[0].start]
    suffix = inner_text[groups[-1].end :]
    setup_prefix, visible_prefix = _split_rewrite_setup_blocks(prefix)
    if _contains_rewrite_unsafe_tail_control(suffix):
        return None
    if not _contains_translatable_text(prefix) or not _visible_words(suffix):
        return None
    if _visible_text_for_rewrite(prefix).rstrip().endswith((".", "!", "?", ":", ";")):
        return None
    gaps = [
        inner_text[left.end : right.start] for left, right in zip(groups, groups[1:], strict=False)
    ]
    if any(gap.strip() for gap in gaps):
        return None
    if not all(
        _is_simple_branch_sentence_fragment(
            inner_text[group.branches[0].start : group.branches[0].end]
        )
        for group in groups
    ):
        return None

    rewritten_parts: list[str] = []
    rewritten_parts.append(setup_prefix)
    for index, group in enumerate(groups):
        branch = group.branches[0]
        branch_body = inner_text[branch.start : branch.end]
        if _jinja_block_trims_following_whitespace(branch.opener_text):
            branch_body = branch_body.lstrip()
        if branch.rstrip_body:
            branch_body = branch_body.rstrip()
        branch_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=branch_body,
            opener_text=branch.opener_text,
        )
        suffix_after_group = (
            suffix.lstrip() if _jinja_block_trims_following_whitespace(group.end_text) else suffix
        )
        rewritten_parts.append(branch.opener_text)
        rewritten_parts.append(opening_tag)
        rewritten_parts.append(branch_prefix)
        rewritten_parts.append("".join(gaps[:index]))
        rewritten_parts.append(branch_body)
        rewritten_parts.append("".join(gaps[index:]))
        rewritten_parts.append(suffix_after_group)
        rewritten_parts.append(closing_tag)
        rewritten_parts.append(group.end_text)
    return "".join(rewritten_parts)


def _split_rewrite_setup_blocks(prefix: str) -> tuple[str, str]:
    """Move non-rendering setup blocks before rewritten branch conditions.

    Some upstream sentences compute a branch selector inside the HTML tag, after
    a shared text prefix. If we duplicate that sentence into if/elif branches,
    the selector must be evaluated before the rewritten branch opener.
    """

    tokens = _lex_source_tokens(prefix)
    setup_parts: list[str] = []
    visible_parts: list[str] = []
    cursor = 0

    for token in tokens:
        if token.kind == "jinja_block" and _is_rewrite_setup_block(token.text):
            segment = prefix[cursor : token.start]
            if _jinja_block_trims_previous_whitespace(token.text):
                segment = segment.rstrip()
            visible_parts.append(segment)
            setup_parts.append(token.text)
            cursor = token.end
            if _jinja_block_trims_following_whitespace(token.text):
                while cursor < len(prefix) and prefix[cursor].isspace():
                    cursor += 1

    visible_parts.append(prefix[cursor:])
    return "".join(setup_parts), "".join(visible_parts)


def _branch_prefix_for_rewrite(
    *,
    visible_prefix: str,
    branch_body: str,
    opener_text: str,
) -> str:
    if not _jinja_block_trims_previous_whitespace(opener_text):
        return visible_prefix

    trimmed_prefix = visible_prefix.rstrip()
    if trimmed_prefix == visible_prefix:
        return trimmed_prefix
    if not _should_restore_single_trimmed_space(trimmed_prefix, branch_body):
        return trimmed_prefix
    return f'{trimmed_prefix}{{{{" "}}}}'


def _should_restore_single_trimmed_space(prefix: str, branch_body: str) -> bool:
    if not prefix or not branch_body:
        return False
    visible_prefix = _visible_text_for_rewrite(prefix)
    visible_branch = _visible_text_for_rewrite(branch_body)
    if not visible_prefix or not visible_branch:
        return False
    if visible_prefix.endswith((".", "!", "?", ";", "(", "[", "{", "/", "-", "–")):
        return False
    return True


def _is_rewrite_setup_block(token_text: str) -> bool:
    inner = _jinja_block_inner(token_text)
    keyword = inner.split(None, 1)[0] if inner else ""
    if keyword == "do":
        return True
    if keyword == "set":
        return "=" in inner
    return False


def _contains_rewrite_unsafe_tail_control(source_text: str) -> bool:
    """Avoid moving branch tails that contain loop-scoped or setup-only code."""

    unsafe_keywords = {"do", "for", "endfor", "set"}
    return any(
        token.kind == "jinja_block" and _jinja_block_keyword(token.text) in unsafe_keywords
        for token in _lex_source_tokens(source_text)
    )


def _is_single_choice_context(active_conditions: list[str]) -> bool:
    return any(re.search(r"(^|[^=!<>])==\s*1(\D|$)", condition) for condition in active_conditions)


def _is_simple_branch_sentence_fragment(source_text: str) -> bool:
    if not (_contains_translatable_text(source_text) or _visible_words(source_text)):
        return False
    tokens = _lex_source_tokens(source_text)
    for token in tokens:
        if token.kind == "jinja_block":
            return False
        if token.kind == "html_tag" and token.tag_name not in {
            "a",
            "em",
            "small",
            "span",
            "strong",
        }:
            return False
    return True


def _replace_non_overlapping_regions(
    source_text: str, replacements: list[tuple[int, int, str]]
) -> str:
    parts: list[str] = []
    cursor = 0
    for start, end, replacement in sorted(replacements, key=lambda item: item[0]):
        if start < cursor:
            continue
        parts.append(source_text[cursor:start])
        parts.append(replacement)
        cursor = end
    parts.append(source_text[cursor:])
    return "".join(parts)
