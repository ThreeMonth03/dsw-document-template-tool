"""Language-specific polish for synced translated template output."""

from __future__ import annotations

import re
from pathlib import Path

_CJK = "\u3400-\u9fff"
_CJK_OR_JINJA_END_CLASS = _CJK + "）】》』」}"
_FULLWIDTH_PUNCTUATION_BEFORE_CJK = "。：；，、）】》』」"
_FAIRSHARING_MACRO_LINE_PATTERN = re.compile(
    r"(?m)^([ \t]*):\s*(\{\{\s*macros\.integrationFairSharing\([^}\n]+\)\s*\}\})\."
)
_LOOP_COMMA_PERIOD_PATTERN = re.compile(r'\{\{\s*", "\s+if\s+not\s+loop\.last\s+else\s+"\."\s*\}\}')
_JOIN_COMMA_PATTERN = re.compile(r'\|\s*join\(", "\)')
_INLINE_COLON_PREFIX_PATTERN = re.compile(r'\{\{\s*": "\s*~')
_INLINE_PERIOD_FALLBACK_PATTERN = re.compile(r'\s+else\s+"\."\s*\}\}')


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

    text = _FAIRSHARING_MACRO_LINE_PATTERN.sub(r"\1：\2。", text)
    text = _LOOP_COMMA_PERIOD_PATTERN.sub('{{ "、" if not loop.last else "。" }}', text)
    text = _JOIN_COMMA_PATTERN.sub('|join("、")', text)
    text = _INLINE_COLON_PREFIX_PATTERN.sub('{{ "：" ~', text)
    text = _INLINE_PERIOD_FALLBACK_PATTERN.sub(' else "。" }}', text)
    text = text.replace(
        "{% if not loop.last %}, {% endif %}",
        "{% if not loop.last %}、{% endif %}",
    )
    text = re.sub(r"(\{%-\s*else\s*-%})\.", r"\1。", text)
    text = re.sub(rf"(?<=[{_CJK_OR_JINJA_END_CLASS}])\s*:\s*", "：", text)
    text = re.sub(rf"(?<=[{_CJK_OR_JINJA_END_CLASS}])\.", "。", text)
    text = re.sub(rf"(?<=[{_FULLWIDTH_PUNCTUATION_BEFORE_CJK}])[ \t]+(?=[{_CJK}])", "", text)
    text = re.sub(rf"(?<=[{_CJK}])、\s+", "、", text)
    text = re.sub(rf"(?<=[{_CJK}]),\s+(?=[{_CJK}])", "、", text)
    return text
