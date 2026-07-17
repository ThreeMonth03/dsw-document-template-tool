"""Language-specific polish for synced translated template output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_CJK = "\u3400-\u9fff"
_CJK_OR_JINJA_END_CLASS = _CJK + "）】》』」}"
_FULLWIDTH_PUNCTUATION_BEFORE_CJK = "。：；，、）】》』」"
_FULLWIDTH_BOUNDARY_BEFORE_SILENT_JINJA_CJK = "。：；）】》』」"
_VISIBLE_BOUNDARY_BEFORE_SILENT_JINJA_CJK = _CJK_OR_JINJA_END_CLASS + "。：；>"
_FAIRSHARING_MACRO_LINE_PATTERN = re.compile(
    r"(?m)^([ \t]*):\s*(\{\{\s*macros\.integrationFairSharing\([^}\n]+\)\s*\}\})\."
)
_LOOP_COMMA_PERIOD_PATTERN = re.compile(r'\{\{\s*", "\s+if\s+not\s+loop\.last\s+else\s+"\."\s*\}\}')
_JOIN_COMMA_PATTERN = re.compile(r'\|\s*join\(", "\)')
_SENTENCE_LIST_JOIN_SPACE_PATTERN = re.compile(
    r"""(?P<name>\b(?:[A-Za-z_][A-Za-z0-9_]*)?sentences)\|\s*join\((?P<quote>["']) (?P=quote)\)""",
    re.IGNORECASE,
)
_INLINE_COLON_PREFIX_PATTERN = re.compile(r'\{\{\s*": "\s*~')
_INLINE_PERIOD_FALLBACK_PATTERN = re.compile(r'\s+else\s+"\."\s*\}\}')
_INLINE_TAG_BEFORE_FULLWIDTH_PAREN_PATTERN = re.compile(r"(</(?:em|span|strong)>)\s+（")
_JINJA_STRING_TRAILING_FULLWIDTH_GAP_PATTERN = re.compile(
    rf"(?<=[{_FULLWIDTH_PUNCTUATION_BEFORE_CJK}])[ \t]+(?=['\"])",
)
_DOT_FILTER_PLACEHOLDERS_WITH_TRANSLATED_PUNCTUATION = (
    "swPIDReply",
    "publishedDataHowLongFixed",
    "publishedDataIdentifierSpecifyReply",
    "embargoPeriod",
)
_COST_DESCRIPTION_DOT_PATTERN = re.compile(
    r'\{\{\s*" - "\s*\+\s*projectCostItemDescriptionReply\|dot\s*\}\}'
)
_COST_DESCRIPTION_DOT_REPLACEMENT = (
    "{%- set __tr_dot_value = projectCostItemDescriptionReply|trim -%}"
    '{%- if __tr_dot_value -%}{{ " - " + __tr_dot_value }}'
    '{{ "。" if __tr_dot_value[-1] not in ".。!！?？" else "" }}{%- endif -%}'
)
_REMAINING_DOT_FILTER_PATTERN = re.compile(r"\|dot\b")


@dataclass(frozen=True)
class SilentSpacingCollapse:
    """Silent Jinja tags to keep while removing following visible whitespace."""

    silent_tags: list[str]
    next_index: int


def _is_cjk(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff"


def _read_silent_jinja_tag(text: str, start: int) -> tuple[str, int] | None:
    """Read a non-outputting Jinja tag at `start`, if one is present."""

    if text.startswith("{%", start):
        end_marker = "%}"
    elif text.startswith("{#", start):
        end_marker = "#}"
    else:
        return None

    end = text.find(end_marker, start + 2)
    if end == -1:
        return None
    end += len(end_marker)
    return text[start:end], end


def _collapse_fullwidth_spacing_before_cjk(text: str) -> str:
    """Remove visible whitespace between Chinese punctuation and Chinese text.

    Jinja control/comment tags do not emit visible text, but the surrounding
    template newlines do. Keep those tags while stripping only the whitespace
    that would become an unwanted half-width gap in rendered zh-Hant output.
    """

    result: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        result.append(char)
        index += 1

        if char not in _FULLWIDTH_PUNCTUATION_BEFORE_CJK:
            continue

        lookahead = index
        silent_tags: list[str] = []
        allow_silent_tags = char in _FULLWIDTH_BOUNDARY_BEFORE_SILENT_JINJA_CJK
        while True:
            while lookahead < len(text) and text[lookahead] in " \t\r\n":
                lookahead += 1

            if not allow_silent_tags:
                break

            silent_tag = _read_silent_jinja_tag(text, lookahead)
            if silent_tag is None:
                break

            tag_text, lookahead = silent_tag
            silent_tags.append(tag_text)

        if lookahead > index and lookahead < len(text) and _is_cjk(text[lookahead]):
            result.extend(silent_tags)
            index = lookahead

    return "".join(result)


def _collapse_silent_jinja_leading_spacing_before_cjk(text: str) -> str:
    """Remove indentation emitted after silent Jinja branches before zh-Hant text."""

    result: list[str] = []
    index = 0
    last_visible_char = ""
    while index < len(text):
        silent_tag = _read_silent_jinja_tag(text, index)
        if silent_tag is not None:
            tag_text, tag_end = silent_tag
            collapse = _silent_spacing_collapse_after_tag(
                text=text,
                tag_text=tag_text,
                tag_end=tag_end,
                last_visible_char=last_visible_char,
            )
            if collapse is not None:
                while result and result[-1].isspace():
                    result.pop()
                result.extend(collapse.silent_tags)
                index = collapse.next_index
                continue

            result.append(tag_text)
            index = tag_end
            continue

        char = text[index]
        result.append(char)
        if not char.isspace():
            last_visible_char = char
        index += 1

    return "".join(result)


def _silent_spacing_collapse_after_tag(
    *,
    text: str,
    tag_text: str,
    tag_end: int,
    last_visible_char: str,
) -> SilentSpacingCollapse | None:
    if last_visible_char not in _VISIBLE_BOUNDARY_BEFORE_SILENT_JINJA_CJK:
        return None

    lookahead = tag_end
    silent_tags = [tag_text]
    while True:
        while lookahead < len(text) and text[lookahead] in " \t\r\n":
            lookahead += 1

        next_silent_tag = _read_silent_jinja_tag(text, lookahead)
        if next_silent_tag is None:
            break

        next_tag_text, lookahead = next_silent_tag
        silent_tags.append(next_tag_text)

    if lookahead <= tag_end or lookahead >= len(text):
        return None
    if not (_is_cjk(text[lookahead]) or text[lookahead] == "（"):
        return None
    return SilentSpacingCollapse(silent_tags=silent_tags, next_index=lookahead)


def polish_translated_output_dir(*, output_dir: Path, target_lang: str) -> None:
    """Apply safe, text-level polish after translations are synced.

    Translation units intentionally avoid owning surrounding Jinja punctuation.
    For zh-Hant output, a few punctuation marks from the English template remain
    outside translation blocks, so normalize them at the final output boundary.
    """

    if target_lang != "zh_Hant":
        return

    for path in (output_dir / "src").rglob("*.j2"):
        path.write_text(
            polish_zh_hant_template_text(path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )


def polish_zh_hant_template_text(text: str) -> str:
    """Normalize punctuation patterns that are outside translation units."""

    text = _normalize_dot_filters(text)
    text = _normalize_template_punctuation(text)
    text = _collapse_silent_jinja_leading_spacing_before_cjk(text)
    text = _collapse_fullwidth_spacing_before_cjk(text)
    text = re.sub(rf"(?<=[{_CJK}])、\s+", "、", text)
    text = re.sub(rf"(?<=[{_CJK}]),\s+(?=[{_CJK}])", "、", text)
    return text


def _normalize_dot_filters(text: str) -> str:
    for placeholder in _DOT_FILTER_PLACEHOLDERS_WITH_TRANSLATED_PUNCTUATION:
        text = re.sub(
            r"\{\{\s*" + re.escape(placeholder) + r"\|dot\s*\}\}",
            "{{ " + placeholder + "|trim }}",
            text,
        )
    text = _COST_DESCRIPTION_DOT_PATTERN.sub(_COST_DESCRIPTION_DOT_REPLACEMENT, text)
    text = _REMAINING_DOT_FILTER_PATTERN.sub("|trim", text)
    return text


def _normalize_template_punctuation(text: str) -> str:
    text = _FAIRSHARING_MACRO_LINE_PATTERN.sub(r"\1：\2。", text)
    text = _LOOP_COMMA_PERIOD_PATTERN.sub('{{ "、" if not loop.last else "。" }}', text)
    text = _JOIN_COMMA_PATTERN.sub('|join("、")', text)
    text = _SENTENCE_LIST_JOIN_SPACE_PATTERN.sub(r'\g<name>|join("")', text)
    text = _INLINE_COLON_PREFIX_PATTERN.sub('{{ "：" ~', text)
    text = _INLINE_PERIOD_FALLBACK_PATTERN.sub(' else "。" }}', text)
    text = text.replace(
        "{% if not loop.last %}, {% endif %}",
        "{% if not loop.last %}、{% endif %}",
    )
    text = re.sub(r"(\{%-\s*else\s*-%})\.", r"\1。", text)
    text = re.sub(rf"(?<=[{_CJK_OR_JINJA_END_CLASS}])\s*:\s*", "：", text)
    text = _JINJA_STRING_TRAILING_FULLWIDTH_GAP_PATTERN.sub("", text)
    text = re.sub(rf"(?<=[{_CJK_OR_JINJA_END_CLASS}])\s+（", "（", text)
    text = _INLINE_TAG_BEFORE_FULLWIDTH_PAREN_PATTERN.sub(r"\1（", text)
    text = re.sub(rf"(?<=[{_CJK_OR_JINJA_END_CLASS}])\.", "。", text)
    text = text.replace("。.", "。")
    return text
