"""Reversible rewrites for sentence-building Jinja append statements."""

from __future__ import annotations

import ast
import re

from .jinja_blocks import jinja_block_inner
from .jinja_literals import is_translatable_jinja_literal
from .markers import decode_marker_payload, encode_marker_payload
from .models import TemplateTransformError
from .scanner import JINJA_BLOCK_PATTERN

APPEND_SENTENCE_REWRITE_PATTERN = re.compile(
    r"\{# __tr_append_sentence_original:(?P<payload>[A-Za-z0-9_-]+=*) #\}"
    r".*?"
    r"\{# __tr_append_sentence_original:end -?#\}",
    re.DOTALL,
)


def rewrite_append_sentence_literals(source_text: str) -> str:
    """Turn concatenated append literals into editable sentence set-blocks.

    Upstream templates sometimes build rendered sentences with Jinja-only code,
    e.g. `sentences.append("Before " ~ value ~ " after.")`.  Exporting each
    string literal separately makes translators handle broken fragments.  The
    set-block keeps rendered output equivalent while exposing one complete
    sentence with normal `{{ value }}` placeholders.
    """

    append_index = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal append_index
        original = match.group(0)
        if not (original.startswith("{%-") and original.rstrip().endswith("-%}")):
            return original

        inner = jinja_block_inner(original)
        append_match = re.fullmatch(
            r"(?:(?P<mode>do)|set\s+(?P<set_name>[A-Za-z_][A-Za-z0-9_]*)\s*=)\s+"
            r"(?P<target>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
            r"\.append\((?P<arg>.*)\)",
            inner,
            flags=re.DOTALL,
        )
        if append_match is None:
            return original

        sentence = _jinja_concat_expression_to_sentence(append_match.group("arg"))
        if sentence is None:
            return original

        variable_name = f"__tr_append_sentence_{append_index:04d}"
        append_index += 1
        encoded_original = encode_marker_payload(original)
        target = append_match.group("target")
        return (
            f"{{# __tr_append_sentence_original:{encoded_original} #}}"
            f"{{%- set {variable_name} -%}}"
            f"{sentence}"
            "{%- endset -%}"
            f"{_append_sentence_rewrite_statement(append_match, target, variable_name)}"
            "{# __tr_append_sentence_original:end -#}"
        )

    return JINJA_BLOCK_PATTERN.sub(replace, source_text)


def restore_append_sentence_rewrites(source_text: str) -> str:
    """Restore original append statements when compacting a workspace."""

    def replace(match: re.Match[str]) -> str:
        try:
            return decode_marker_payload(match.group("payload"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise TemplateTransformError("Invalid append sentence rewrite marker") from exc

    return APPEND_SENTENCE_REWRITE_PATTERN.sub(replace, source_text)


def _append_sentence_rewrite_statement(
    append_match: re.Match[str],
    target: str,
    variable_name: str,
) -> str:
    if append_match.group("mode") == "do":
        return f"{{%- do {target}.append({variable_name}) -%}}"
    set_name = append_match.group("set_name") or "_"
    return f"{{%- set {set_name} = {target}.append({variable_name}) -%}}"


def _jinja_concat_expression_to_sentence(expr: str) -> str | None:
    parts = _split_top_level_concat(expr)
    if len(parts) < 2:
        return None

    rendered_parts: list[str] = []
    literal_count = 0
    expression_count = 0
    for part in parts:
        literal = _literal_part_to_text(part)
        if literal is not None:
            if is_translatable_jinja_literal(literal):
                literal_count += 1
            rendered_parts.append(literal)
            continue

        normalized = part.strip()
        if not normalized:
            return None
        expression_count += 1
        rendered_parts.append("{{ " + normalized + " }}")

    if literal_count == 0 or expression_count == 0:
        return None
    return "".join(rendered_parts)


def _literal_part_to_text(part: str) -> str | None:
    stripped = part.strip()
    if not (
        (stripped.startswith('"') and stripped.endswith('"'))
        or (stripped.startswith("'") and stripped.endswith("'"))
    ):
        return None
    try:
        value = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, str) else None


def _split_top_level_concat(expr: str) -> list[str]:
    parts: list[str] = []
    quote: str | None = None
    escape_next = False
    bracket_depth = 0
    start = 0

    for index, char in enumerate(expr):
        if quote is not None:
            if escape_next:
                escape_next = False
            elif char == "\\":
                escape_next = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "([{":
            bracket_depth += 1
            continue
        if char in ")]}":
            bracket_depth = max(0, bracket_depth - 1)
            continue
        if char == "~" and bracket_depth == 0:
            parts.append(expr[start:index])
            start = index + 1

    parts.append(expr[start:])
    return parts
