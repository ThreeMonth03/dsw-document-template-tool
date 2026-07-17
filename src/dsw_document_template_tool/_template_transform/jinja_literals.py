"""Helpers for identifying translator-visible Jinja string literals."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from .jinja_blocks import jinja_block_inner
from .scanner import (
    JINJA_BLOCK_PATTERN,
    JINJA_EXPR_PATTERN,
    JINJA_STRING_LITERAL_PATTERN,
    UUID_LITERAL_PATTERN,
)

IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STRING_LIST_INITIALIZER_PATTERN = re.compile(
    r"set\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>\[.*\])",
    re.DOTALL,
)


@dataclass(frozen=True)
class JinjaStringListInitializer:
    """One static string-list assignment inside a Jinja statement."""

    name: str
    literals: tuple[str, ...]


def extract_translatable_jinja_block_literals(block_body: str) -> list[str]:
    """Return user-facing literals from Jinja statements that feed rendered output."""

    inner = block_body.strip().strip("-").strip()
    if ".append(" not in inner:
        return []
    return extract_translatable_jinja_literals(inner)


def parse_jinja_string_list_initializer(
    block_body: str,
) -> JinjaStringListInitializer | None:
    """Parse a Jinja ``set name = ['text']`` statement without evaluating code."""

    inner = jinja_block_inner("{% " + block_body + " %}")
    match = STRING_LIST_INITIALIZER_PATTERN.fullmatch(inner)
    if match is None:
        return None
    try:
        value = ast.literal_eval(match.group("value"))
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        return None
    literals = tuple(item.strip() for item in value if item.strip())
    if not literals:
        return None
    return JinjaStringListInitializer(name=match.group("name"), literals=literals)


def rendered_joined_collection_names(source_text: str) -> set[str]:
    """Return simple collection names rendered through a Jinja ``join`` filter."""

    names: set[str] = set()
    for match in JINJA_EXPR_PATTERN.finditer(source_text):
        pipeline = match.group("expr").split("|")
        if len(pipeline) < 2 or not any(
            re.match(r"\s*join(?:\s*\(|\s*$)", stage) for stage in pipeline[1:]
        ):
            continue
        candidate = pipeline[0].strip()
        if IDENTIFIER_PATTERN.fullmatch(candidate):
            names.add(candidate)
    return names


def translatable_rendered_list_initializer_literals(
    *, token_text: str, rendered_collection_names: set[str]
) -> tuple[str, ...]:
    """Return literals from a static list that is proven to feed rendered output."""

    match = JINJA_BLOCK_PATTERN.fullmatch(token_text)
    if match is None:
        return ()
    initializer = parse_jinja_string_list_initializer(match.group("body"))
    if initializer is None or initializer.name not in rendered_collection_names:
        return ()
    return initializer.literals


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
