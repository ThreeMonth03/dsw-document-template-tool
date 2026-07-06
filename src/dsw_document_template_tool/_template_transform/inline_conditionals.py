"""Reversible rewrites for inline Jinja conditional expressions."""

from __future__ import annotations

import re

from .jinja_literals import extract_translatable_jinja_literals
from .markers import decode_marker_payload, encode_marker_payload
from .models import TemplateTransformError
from .scanner import JINJA_EXPR_PATTERN

INLINE_CONDITIONAL_REWRITE_PATTERN = re.compile(
    r"\{# __tr_inline_if_original:(?P<payload>[A-Za-z0-9_-]+=*) #\}"
    r".*?"
    r"\{# __tr_inline_if_original:end #\}",
    re.DOTALL,
)


def rewrite_inline_conditional_expressions(source_text: str) -> str:
    """Expand inline Jinja ternaries so fallback strings can be translated safely."""

    def replace(match: re.Match[str]) -> str:
        original = match.group(0)
        parts = _split_inline_conditional_expression(match.group("expr"))
        if parts is None:
            return original
        true_expr, condition_expr, false_expr = parts
        if not _should_rewrite_inline_conditional(true_expr=true_expr, false_expr=false_expr):
            return original
        encoded_original = encode_marker_payload(original)
        return (
            f"{{# __tr_inline_if_original:{encoded_original} #}}"
            f"{{% if {condition_expr} %}}{{{{ {true_expr} }}}}"
            f"{{% else %}}{{{{ {false_expr} }}}}{{% endif %}}"
            "{# __tr_inline_if_original:end #}"
        )

    return JINJA_EXPR_PATTERN.sub(replace, source_text)


def restore_inline_conditional_rewrites(source_text: str) -> str:
    """Restore original inline ternaries when compacting an expanded workspace."""

    def replace(match: re.Match[str]) -> str:
        try:
            return decode_marker_payload(match.group("payload"))
        except ValueError as exc:
            raise TemplateTransformError("Invalid inline conditional rewrite marker") from exc

    return INLINE_CONDITIONAL_REWRITE_PATTERN.sub(replace, source_text)


def _split_inline_conditional_expression(expr: str) -> tuple[str, str, str] | None:
    normalized = expr.strip()
    if not normalized:
        return None
    if_index = _find_top_level_keyword(normalized, "if", start=0)
    if if_index is None:
        return None
    else_index = _find_top_level_keyword(normalized, "else", start=if_index + len("if"))
    if else_index is None:
        return None

    true_expr = normalized[:if_index].strip()
    condition_expr = normalized[if_index + len("if") : else_index].strip()
    false_expr = normalized[else_index + len("else") :].strip()
    if not true_expr or not condition_expr or not false_expr:
        return None
    return true_expr, condition_expr, false_expr


def _find_top_level_keyword(expr: str, keyword: str, *, start: int) -> int | None:
    quote: str | None = None
    escape_next = False
    bracket_depth = 0
    index = start
    while index < len(expr):
        char = expr[index]
        if quote is not None:
            if escape_next:
                escape_next = False
            elif char == "\\":
                escape_next = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if char in "([{":
            bracket_depth += 1
            index += 1
            continue
        if char in ")]}":
            bracket_depth = max(0, bracket_depth - 1)
            index += 1
            continue
        if bracket_depth == 0 and expr.startswith(keyword, index):
            before = expr[index - 1] if index > 0 else " "
            after_index = index + len(keyword)
            after = expr[after_index] if after_index < len(expr) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                return index
        index += 1
    return None


def _should_rewrite_inline_conditional(*, true_expr: str, false_expr: str) -> bool:
    return _expr_has_translatable_literal(true_expr) or _expr_has_translatable_literal(false_expr)


def _expr_has_translatable_literal(expr: str) -> bool:
    return bool(extract_translatable_jinja_literals(expr))
