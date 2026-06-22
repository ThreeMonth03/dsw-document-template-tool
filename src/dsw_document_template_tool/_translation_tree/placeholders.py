"""Translator placeholder validation and materialization.

The merge workflow will use these helpers before carrying translations from an
old tree into a new tree. Keeping the rules here prevents export, sync, audit,
and migration code from drifting apart.
"""

from __future__ import annotations

import ast
import re
from collections import Counter

from dsw_document_template_tool._template_transform.jinja_literals import (
    extract_translatable_jinja_literals as _extract_translatable_jinja_literals,
)

from .models import TranslationTreeError
from .syntax import HTML_TAG_PATTERN, JINJA_EXPR_PATTERN

TRANSLATOR_PLACEHOLDER_PATTERN = re.compile(r"(?<!\{)\{(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\}(?!\})")
RAW_JINJA_IN_TRANSLATION_PATTERN = re.compile(r"\{[#%{]")


def validate_translation_placeholders(
    *,
    source_file: str,
    unit_key: str,
    translation_document_path: str | None,
    source_text: str,
    translation_text: str,
) -> None:
    """Validate that a translation preserves source placeholders safely."""

    if contains_raw_jinja_in_translation(translation_text):
        location = format_translation_location(
            source_file,
            unit_key,
            translation_document_path,
        )
        raise TranslationTreeError(
            "Translation contains raw Jinja syntax for "
            f"{location}. Use translator placeholders such as `{{name}}` instead."
        )

    source_counts = source_placeholder_counts(source_text)
    if not source_counts and not extract_translator_placeholder_names(translation_text):
        return

    placeholder_map = build_source_placeholder_map(source_text)
    shorthand_names = extract_translator_placeholder_names(translation_text)
    unknown_shorthand_names = sorted(set(shorthand_names) - set(placeholder_map))
    if unknown_shorthand_names:
        formatted_names = ", ".join(f"{{{name}}}" for name in unknown_shorthand_names)
        location = format_translation_location(
            source_file,
            unit_key,
            translation_document_path,
        )
        raise TranslationTreeError(
            "Translation uses placeholder names that cannot be mapped back to Jinja "
            f"for {location}: {formatted_names}"
        )

    translation_counts = translation_placeholder_counts(translation_text)
    unexpected_placeholder_names = sorted(set(translation_counts) - set(source_counts))
    if unexpected_placeholder_names:
        formatted_names = ", ".join(f"{{{name}}}" for name in unexpected_placeholder_names)
        location = format_translation_location(
            source_file,
            unit_key,
            translation_document_path,
        )
        raise TranslationTreeError(
            "Translation introduces placeholders that are not present in the source for "
            f"{location}: {formatted_names}"
        )

    missing_counts = source_counts - translation_counts
    if missing_counts:
        formatted_names = ", ".join(
            f"{{{name}}}" if count == 1 else f"{{{name}}} x{count}"
            for name, count in sorted(missing_counts.items())
        )
        location = format_translation_location(
            source_file,
            unit_key,
            translation_document_path,
        )
        raise TranslationTreeError(
            f"Translation is missing required placeholders for {location}: {formatted_names}"
        )


def format_translation_location(
    source_file: str,
    unit_key: str,
    translation_document_path: str | None,
) -> str:
    """Format a stable, human-readable translation unit location."""

    location = f"{source_file} ({unit_key})"
    if translation_document_path:
        location = f"{location} in {translation_document_path}"
    return location


def source_placeholder_counts(source_text: str) -> Counter[str]:
    """Count translator-visible placeholders required by a source unit."""

    counts: Counter[str] = Counter()
    for match in JINJA_EXPR_PATTERN.finditer(visible_placeholder_source_text(source_text)):
        for name in extract_translator_placeholder_names(
            jinja_expr_to_placeholder(match.group("expr"))
        ):
            counts[name] += 1
    return counts


def translation_placeholder_counts(translation_text: str) -> Counter[str]:
    """Count placeholders used by translated text."""

    counts: Counter[str] = Counter(extract_translator_placeholder_names(translation_text))
    for match in JINJA_EXPR_PATTERN.finditer(translation_text):
        for name in extract_translator_placeholder_names(
            jinja_expr_to_placeholder(match.group("expr"))
        ):
            counts[name] += 1
    return counts


def build_source_placeholder_map(source_text: str) -> dict[str, str]:
    """Map translator placeholder names back to source Jinja expressions."""

    expressions_by_name: dict[str, set[str]] = {}
    for match in JINJA_EXPR_PATTERN.finditer(visible_placeholder_source_text(source_text)):
        expression = " ".join(match.group("expr").strip().split())
        placeholder_names = extract_translator_placeholder_names(
            jinja_expr_to_placeholder(match.group("expr"))
        )
        for name in placeholder_names:
            expressions_by_name.setdefault(name, set()).add(expression)
    return {
        name: next(iter(expressions))
        for name, expressions in expressions_by_name.items()
        if len(expressions) == 1
    }


def extract_translator_placeholder_names(source_text: str) -> list[str]:
    """Return translator placeholder names such as ``name`` from ``{name}``."""

    return [match.group("name") for match in TRANSLATOR_PLACEHOLDER_PATTERN.finditer(source_text)]


def materialize_translation_placeholders(*, source_text: str, translation_text: str) -> str:
    """Replace translator placeholders with their original Jinja expressions."""

    placeholder_map = build_source_placeholder_map(source_text)

    def replace_placeholder(match: re.Match[str]) -> str:
        name = match.group("name")
        expression = placeholder_map.get(name)
        if expression is None:
            return match.group(0)
        return "{{ " + expression + " }}"

    return TRANSLATOR_PLACEHOLDER_PATTERN.sub(replace_placeholder, translation_text)


def visible_placeholder_source_text(source_text: str) -> str:
    """Return source text that translators can actually see and rearrange.

    Attribute-only Jinja expressions such as ``href="{{ url }}"`` are machine
    wiring. They must not force translators to duplicate placeholders that are
    already visible inside the link text.
    """

    return HTML_TAG_PATTERN.sub(" ", source_text)


def contains_raw_jinja_in_translation(translation_text: str) -> bool:
    """Return true when translator text contains raw Jinja syntax."""

    return RAW_JINJA_IN_TRANSLATION_PATTERN.search(translation_text) is not None


def jinja_expr_to_placeholder(expr: str) -> str:
    """Convert a visible Jinja expression into a translator placeholder."""

    normalized = " ".join(expr.strip().split())
    literal_value = literal_expr_to_text(normalized)
    if literal_value is not None:
        return literal_value
    literals = _extract_translatable_jinja_literals(expr)
    fallback_match = re.match(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+if\s+", normalized)
    if fallback_match is not None:
        placeholder = "{" + fallback_match.group("name") + "}"
        if literals:
            return f"{placeholder} / {' / '.join(literals)}"
        return placeholder
    if literals:
        return " / ".join(literals)
    base = normalized.split("|", 1)[0].strip()
    indexed_placeholder = indexed_expr_to_placeholder(base)
    if indexed_placeholder is not None:
        return indexed_placeholder
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", base):
        return "{" + base + "}"
    inferred_placeholder = identifier_expr_to_placeholder(base)
    if inferred_placeholder is not None:
        return inferred_placeholder
    return "{value}"


def identifier_expr_to_placeholder(expr: str) -> str | None:
    """Infer a stable placeholder name from computed expressions."""

    without_literals = re.sub(
        r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
        " ",
        expr,
        flags=re.DOTALL,
    )
    without_filters = re.sub(r"\|[A-Za-z_][A-Za-z0-9_]*", " ", without_literals)
    without_call_names = re.sub(
        r"\b[A-Za-z_][A-Za-z0-9_.]*\s*(?=\()",
        " ",
        without_filters,
    )
    without_attr_prefixes = re.sub(
        r"\b[A-Za-z_][A-Za-z0-9_]*\.",
        "",
        without_call_names,
    )
    reserved_words = {
        "and",
        "else",
        "false",
        "if",
        "in",
        "is",
        "none",
        "not",
        "or",
        "true",
    }
    names: list[str] = []
    for match in re.finditer(r"\b[A-Za-z_][A-Za-z0-9_]*\b", without_attr_prefixes):
        name = match.group(0)
        if name.lower() in reserved_words or name in names:
            continue
        names.append(name)
    if not names:
        return None
    return "{" + "_".join(names[:3]) + "}"


def indexed_expr_to_placeholder(expr: str) -> str | None:
    """Infer a placeholder name for simple indexed expressions."""

    match = re.match(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\[(?P<index>[^\]]+)\]$", expr)
    if match is None:
        return None
    name = match.group("name")
    index = match.group("index").strip()
    if name == "names":
        if ":" in index:
            return "{names}"
        if index == "-1":
            return "{lastName}"
        if index == "0":
            return "{firstName}"
        if index == "1":
            return "{secondName}"
    index_slug = re.sub(r"[^A-Za-z0-9]+", "_", index.replace("-", "minus_")).strip("_")
    if index_slug:
        return "{" + name + "_" + index_slug + "}"
    return "{" + name + "}"


def literal_expr_to_text(expr: str) -> str | None:
    """Return a string literal expression value, if the expression is only literal text."""

    if expr.startswith("+"):
        expr = expr[1:].strip()
    if not (
        (expr.startswith('"') and expr.endswith('"'))
        or (expr.startswith("'") and expr.endswith("'"))
    ):
        return None
    try:
        value = ast.literal_eval(expr)
    except (SyntaxError, ValueError):
        return None
    if isinstance(value, str):
        return value
    return None
