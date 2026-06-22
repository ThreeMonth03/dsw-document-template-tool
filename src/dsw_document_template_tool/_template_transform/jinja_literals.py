"""Helpers for identifying translator-visible Jinja string literals."""

from __future__ import annotations

import ast
import re

from .scanner import JINJA_STRING_LITERAL_PATTERN, UUID_LITERAL_PATTERN


def extract_translatable_jinja_block_literals(block_body: str) -> list[str]:
    """Return user-facing literals from Jinja statements that feed rendered output."""

    inner = block_body.strip().strip("-").strip()
    if ".append(" not in inner:
        return []
    return extract_translatable_jinja_literals(inner)


def extract_translatable_jinja_literals(expr: str) -> list[str]:
    """Return user-facing string literals from a Jinja output expression."""

    literals: list[str] = []
    for match in JINJA_STRING_LITERAL_PATTERN.finditer(expr):
        if is_subscript_literal(expr=expr, start=match.start(), end=match.end()):
            continue
        if is_dict_key_literal(expr=expr, end=match.end()):
            continue
        try:
            value = ast.literal_eval(match.group("literal"))
        except (SyntaxError, ValueError):
            continue
        if isinstance(value, str) and is_translatable_jinja_literal(value):
            literals.append(value.strip())
    return literals


def is_subscript_literal(*, expr: str, start: int, end: int) -> bool:
    """Return true when one literal is used as an index/key lookup."""

    previous_index = start - 1
    while previous_index >= 0 and expr[previous_index].isspace():
        previous_index -= 1

    next_index = end
    while next_index < len(expr) and expr[next_index].isspace():
        next_index += 1

    return (
        previous_index >= 0
        and expr[previous_index] == "["
        and next_index < len(expr)
        and expr[next_index] == "]"
    )


def is_dict_key_literal(*, expr: str, end: int) -> bool:
    """Return true when one literal is a dictionary key declaration."""

    next_index = end
    while next_index < len(expr) and expr[next_index].isspace():
        next_index += 1
    return next_index < len(expr) and expr[next_index] == ":"


def is_translatable_jinja_literal(value: str) -> bool:
    """Return true when a Jinja string literal is likely visible prose."""

    stripped = value.strip()
    if not stripped:
        return False
    if UUID_LITERAL_PATTERN.fullmatch(stripped):
        return False
    if stripped.startswith(("http://", "https://", "mailto:", "ftp://")):
        return False
    if stripped.startswith("<") and stripped.endswith(">"):
        return False
    if re.search(r"%[A-Za-z]", stripped):
        return False
    return re.search(r"[A-Za-z]", stripped) is not None
