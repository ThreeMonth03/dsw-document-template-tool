"""Structural audit for translated expanded templates."""

from __future__ import annotations

import ast
import hashlib
import re
from collections import Counter
from pathlib import Path

from .._template_transform.jinja_literals import (
    is_dict_key_literal as _is_dict_key_literal,
)
from .._template_transform.jinja_literals import (
    is_subscript_literal as _is_subscript_literal,
)
from .._template_transform.jinja_literals import (
    rendered_joined_collection_names as _rendered_collections,
)
from .._template_transform.jinja_literals import (
    translatable_rendered_list_initializer_literals as _rendered_list_literals,
)
from .._template_transform.scanner import (
    JINJA_STRING_LITERAL_PATTERN,
)
from .models import TranslationTreeAuditIssue, TranslationTreeError
from .output_polish import polish_zh_hant_template_text
from .placeholders import literal_expr_to_text
from .syntax import HTML_TAG_PATTERN, JINJA_COMMENT_OR_BLOCK_PATTERN, JINJA_EXPR_PATTERN
from .workspace import validate_expanded_workspace

STRUCTURAL_HTML_ATTRS = {
    "action",
    "class",
    "colspan",
    "content",
    "data-format",
    "data-template",
    "href",
    "id",
    "method",
    "name",
    "rel",
    "rowspan",
    "src",
    "style",
    "target",
    "type",
    "width",
    "height",
}
HTML_ATTR_PATTERN = re.compile(
    r"""(?P<name>[A-Za-z_:][A-Za-z0-9_:.-]*)"""
    r"""(?:\s*=\s*(?P<value>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s"'=<>`]+))?""",
    re.DOTALL,
)
HTML_TAG_NAME_PATTERN = re.compile(r"^<\s*(?P<closing>/)?\s*(?P<name>[A-Za-z][A-Za-z0-9:-]*)")
DECORATIVE_HTML_TAGS = {"em", "small", "strong"}


def audit_translated_template_structure(
    *,
    source_dir: Path,
    output_dir: Path,
) -> list[TranslationTreeAuditIssue]:
    """Return structural differences between expanded and translated templates.

    Translation is allowed to change natural-language text, translatable Jinja
    string literals, and template metadata. It must not change the executable
    Jinja shape, machine placeholders, HTML structure, links/assets, or static
    source assets. This audit is intentionally stricter than `dsw-tdk verify`:
    the template can be syntactically valid and still be structurally wrong.
    """

    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    issues: list[TranslationTreeAuditIssue] = []

    try:
        validate_expanded_workspace(source_dir)
    except TranslationTreeError as exc:
        return [
            TranslationTreeAuditIssue(
                code="invalid-expanded-workspace",
                location=str(source_dir),
                message=str(exc),
            )
        ]

    if not output_dir.is_dir():
        return [
            TranslationTreeAuditIssue(
                code="missing-translated-template",
                location=str(output_dir),
                message="Translated template output directory does not exist.",
            )
        ]

    source_src_dir = source_dir / "src"
    output_src_dir = output_dir / "src"
    if not source_src_dir.is_dir() or not output_src_dir.is_dir():
        return [
            TranslationTreeAuditIssue(
                code="missing-src-directory",
                location=str(output_dir),
                message="Both source and translated templates must contain a src directory.",
            )
        ]

    source_files = _relative_file_set(source_src_dir)
    output_files = _relative_file_set(output_src_dir)
    missing_files = sorted(source_files - output_files)
    extra_files = sorted(output_files - source_files)
    if missing_files:
        issues.append(
            TranslationTreeAuditIssue(
                code="missing-translated-source-file",
                location="src",
                message="Translated output is missing source files: "
                + ", ".join(missing_files[:10]),
            )
        )
    if extra_files:
        issues.append(
            TranslationTreeAuditIssue(
                code="extra-translated-source-file",
                location="src",
                message="Translated output has unexpected source files: "
                + ", ".join(extra_files[:10]),
            )
        )

    for relative_path in sorted(source_files & output_files):
        source_path = source_src_dir / relative_path
        output_path = output_src_dir / relative_path
        if source_path.suffix == ".j2":
            issues.extend(
                _audit_translated_jinja_file_structure(
                    source_path=source_path,
                    output_path=output_path,
                    relative_path=f"src/{relative_path}",
                )
            )
        elif _hash_file(source_path) != _hash_file(output_path):
            issues.append(
                TranslationTreeAuditIssue(
                    code="changed-static-source-asset",
                    location=f"src/{relative_path}",
                    message=(
                        "Static source assets must be identical between expanded "
                        "and translated templates. Put intentional asset changes in "
                        "the expanded template source, not only in translated output."
                    ),
                )
            )

    return issues


def _relative_file_set(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _audit_translated_jinja_file_structure(
    *,
    source_path: Path,
    output_path: Path,
    relative_path: str,
) -> list[TranslationTreeAuditIssue]:
    source_text = _normalize_known_output_polish_for_structure_audit(
        source_path.read_text(encoding="utf-8")
    )
    output_text = _normalize_known_output_polish_for_structure_audit(
        output_path.read_text(encoding="utf-8")
    )
    issues: list[TranslationTreeAuditIssue] = []

    source_control = _jinja_control_signature(source_text)
    output_control = _jinja_control_signature(output_text)
    if source_control != output_control:
        issues.append(
            _sequence_mismatch_issue(
                code="changed-jinja-control-structure",
                location=relative_path,
                label="Jinja block/comment",
                source_sequence=source_control,
                output_sequence=output_control,
            )
        )

    source_expressions = _jinja_expression_signature_counts(source_text)
    output_expressions = _jinja_expression_signature_counts(output_text)
    if source_expressions != output_expressions:
        issues.append(
            _counter_mismatch_issue(
                code="changed-jinja-expression-structure",
                location=relative_path,
                label="Jinja expression",
                source_counts=source_expressions,
                output_counts=output_expressions,
            )
        )

    source_protected_literals = _protected_jinja_literal_counts(source_text)
    output_all_literals = _all_jinja_literal_counts(output_text)
    missing_protected_literals = source_protected_literals - output_all_literals
    if missing_protected_literals:
        issues.append(
            _counter_mismatch_issue(
                code="changed-protected-jinja-literal",
                location=relative_path,
                label="protected Jinja literal missing from translated output",
                source_counts=source_protected_literals,
                output_counts=output_all_literals,
            )
        )

    output_protected_literals = _protected_jinja_literal_counts(output_text)
    source_all_literals = _all_jinja_literal_counts(source_text)
    unexpected_protected_literals = output_protected_literals - source_all_literals
    if unexpected_protected_literals:
        issues.append(
            _counter_mismatch_issue(
                code="introduced-protected-jinja-literal",
                location=relative_path,
                label="protected Jinja literal introduced by translated output",
                source_counts=source_all_literals,
                output_counts=output_protected_literals,
            )
        )

    source_tags = _html_tag_signature(source_text)
    output_tags = _html_tag_signature(output_text)
    if source_tags != output_tags:
        issues.append(
            _sequence_mismatch_issue(
                code="changed-html-structure",
                location=relative_path,
                label="HTML tag",
                source_sequence=source_tags,
                output_sequence=output_tags,
            )
        )

    return issues


def _normalize_known_output_polish_for_structure_audit(text: str) -> str:
    """Apply registered safe output-polish rewrites before comparing structure.

    The translated output may normalize punctuation around Jinja expressions after
    syncing. Audit both sides through the same narrow normalization so these
    registered language-boundary rewrites do not look like structural damage.
    """

    return polish_zh_hant_template_text(text)


def _sequence_mismatch_issue(
    *,
    code: str,
    location: str,
    label: str,
    source_sequence: list[str],
    output_sequence: list[str],
) -> TranslationTreeAuditIssue:
    index = _first_sequence_difference(source_sequence, output_sequence)
    source_value = source_sequence[index] if index < len(source_sequence) else "<missing>"
    output_value = output_sequence[index] if index < len(output_sequence) else "<missing>"
    return TranslationTreeAuditIssue(
        code=code,
        location=location,
        message=(
            f"{label} structure changed at item {index + 1}: "
            f"expanded={source_value!r}, translated={output_value!r}. "
            f"expanded_count={len(source_sequence)}, translated_count={len(output_sequence)}"
        ),
    )


def _counter_mismatch_issue(
    *,
    code: str,
    location: str,
    label: str,
    source_counts: Counter[str],
    output_counts: Counter[str],
) -> TranslationTreeAuditIssue:
    missing = source_counts - output_counts
    unexpected = output_counts - source_counts
    details: list[str] = []
    if missing:
        details.append("missing " + _format_counter_sample(missing))
    if unexpected:
        details.append("unexpected " + _format_counter_sample(unexpected))
    return TranslationTreeAuditIssue(
        code=code,
        location=location,
        message=f"{label} counts changed: " + "; ".join(details),
    )


def _first_sequence_difference(source_sequence: list[str], output_sequence: list[str]) -> int:
    limit = min(len(source_sequence), len(output_sequence))
    for index in range(limit):
        if source_sequence[index] != output_sequence[index]:
            return index
    return limit


def _format_counter_sample(counter: Counter[str]) -> str:
    items = []
    for value, count in sorted(counter.items())[:8]:
        suffix = f" x{count}" if count != 1 else ""
        items.append(f"{value!r}{suffix}")
    return ", ".join(items)


def _jinja_control_signature(source_text: str) -> list[str]:
    signatures: list[str] = []
    for match in JINJA_COMMENT_OR_BLOCK_PATTERN.finditer(source_text):
        token = match.group(0)
        if token.startswith("{#"):
            continue
        else:
            signatures.append("block:" + _normalize_jinja_block_token(token))
    return signatures


def _normalize_jinja_block_token(token: str) -> str:
    trim_left = token.startswith("{%-")
    trim_right = token.endswith("-%}")
    body = token[2:-2].strip()
    if body.startswith("-"):
        body = body[1:].lstrip()
    if body.endswith("-"):
        body = body[:-1].rstrip()
    return (
        ("trim-left|" if trim_left else "")
        + ("trim-right|" if trim_right else "")
        + _normalize_jinja_code(body)
    )


def _normalize_jinja_code(code: str) -> str:
    without_literals = JINJA_STRING_LITERAL_PATTERN.sub("<str>", code)
    return _normalize_structural_whitespace(without_literals)


def _normalize_structural_whitespace(value: str) -> str:
    return " ".join(value.strip().split())


def _jinja_expression_signature_counts(source_text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for match in JINJA_EXPR_PATTERN.finditer(source_text):
        expr = match.group("expr").strip()
        if literal_expr_to_text(expr) is not None:
            continue
        counts[_normalize_jinja_code(expr)] += 1
    return counts


def _all_jinja_literal_counts(source_text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for token in _iter_executable_jinja_tokens(source_text):
        for match in JINJA_STRING_LITERAL_PATTERN.finditer(token):
            literal_value = _literal_match_value(match)
            if literal_value is not None:
                counts[literal_value] += 1
    return counts


def _protected_jinja_literal_counts(source_text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    rendered_names = _rendered_collections(source_text)
    for token in _iter_executable_jinja_tokens(source_text):
        editable_initializer_literals = Counter(
            _rendered_list_literals(
                token_text=token,
                rendered_collection_names=rendered_names,
            )
        )
        for match in JINJA_STRING_LITERAL_PATTERN.finditer(token):
            literal_value = _literal_match_value(match)
            if literal_value is None:
                continue
            normalized_value = literal_value.strip()
            if editable_initializer_literals[normalized_value]:
                editable_initializer_literals[normalized_value] -= 1
                continue
            if _is_protected_jinja_literal(token=token, match=match, value=literal_value):
                counts[literal_value] += 1
    return counts


def _iter_executable_jinja_tokens(source_text: str) -> list[str]:
    tokens = [match.group(0) for match in JINJA_EXPR_PATTERN.finditer(source_text)]
    tokens.extend(
        match.group(0)
        for match in JINJA_COMMENT_OR_BLOCK_PATTERN.finditer(source_text)
        if match.group(0).startswith("{%")
    )
    return tokens


def _literal_match_value(match: re.Match[str]) -> str | None:
    try:
        value = ast.literal_eval(match.group("literal"))
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, str) else None


def _is_protected_jinja_literal(
    *,
    token: str,
    match: re.Match[str],
    value: str,
) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if _is_subscript_literal(expr=token, start=match.start(), end=match.end()):
        return True
    if _is_dict_key_literal(expr=token, end=match.end()):
        return True
    if re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        stripped,
        flags=re.IGNORECASE,
    ):
        return True
    if stripped.startswith(("http://", "https://", "mailto:", "ftp://")):
        return True
    if stripped.startswith("<") and stripped.endswith(">"):
        return True
    return bool(re.search(r"%[A-Za-z]", stripped))


def _html_tag_signature(source_text: str) -> list[str]:
    signatures: list[str] = []
    for match in HTML_TAG_PATTERN.finditer(source_text):
        tag = match.group(0)
        signature = _html_single_tag_signature(tag)
        if signature is not None:
            signatures.append(signature)
    return signatures


def _html_single_tag_signature(tag: str) -> str | None:
    tag = tag.strip()
    if tag.startswith(("<!--", "<!")):
        return _normalize_structural_whitespace(tag)
    name_match = HTML_TAG_NAME_PATTERN.match(tag)
    if name_match is None:
        return None
    name = name_match.group("name").lower()
    if name_match.group("closing"):
        return None
    if name in DECORATIVE_HTML_TAGS:
        return None

    attr_text = tag[name_match.end() :].rstrip(">").rstrip("/").strip()
    attrs = _parse_html_attrs(attr_text)
    attr_parts: list[str] = []
    for attr_name in sorted(attrs):
        attr_name_lower = attr_name.lower()
        attr_value = attrs[attr_name]
        if attr_name_lower in STRUCTURAL_HTML_ATTRS or attr_name_lower.startswith("data-"):
            normalized_value = _normalize_html_attr_value(attr_value)
            attr_parts.append(f"{attr_name_lower}={normalized_value}")
        else:
            attr_parts.append(attr_name_lower)
    closing = "/" if tag.endswith("/>") else ""
    return f"<{name}{closing} {' '.join(attr_parts)}>".rstrip()


def _parse_html_attrs(attr_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in HTML_ATTR_PATTERN.finditer(attr_text):
        name = match.group("name")
        if name.startswith(("/", "{", "%", "#")):
            continue
        value = match.group("value") or ""
        attrs[name.lower()] = value.strip("\"'")
    return attrs


def _normalize_html_attr_value(value: str) -> str:
    normalized = JINJA_STRING_LITERAL_PATTERN.sub("<str>", value)
    normalized = re.sub(
        r"\{\{\s*(.*?)\s*\}\}",
        lambda match: "{{ " + _normalize_jinja_code(match.group(1)) + " }}",
        normalized,
    )
    return _normalize_structural_whitespace(normalized)
