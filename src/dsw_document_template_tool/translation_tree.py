"""Translator-facing tree export and sync for expanded DSW templates."""

from __future__ import annotations

import ast
import hashlib
import html
import json
import os
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .template_transform import (
    ANNOTATABLE_HTML_TAGS,
    GENERATED_BLOCK_PATTERN,
    JINJA_STRING_LITERAL_PATTERN,
    MANIFEST_PATH,
    AnnotationRegion,
    SourceToken,
    _extract_translatable_jinja_block_literals,
    _extract_translatable_jinja_literals,
    _find_matching_tag_end,
    _is_dict_key_literal,
    _is_subscript_literal,
    _is_translatable_jinja_literal,
    _lex_source_tokens,
    generated_block_body,
    generated_block_name,
)

TREE_MANIFEST_PATH = Path(".translation-tree") / "manifest.json"
TREE_VERSION = 2
TREE_ROOT_NAME = "tree"
DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "zh_Hant"
SOURCE_FENCE = "~~~jinja"
TRANSLATION_DOC_NAME = "translation.md"
TRANSLATION_SECTION_PATTERN = re.compile(
    r"### Translation \((?P<target_lang>[^)]+)\)\n\n~~~jinja\n"
    r"(?P<translation_text>.*?)\n~~~\n?\Z",
    re.DOTALL,
)
SENTENCE_SECTION_PATTERN = re.compile(
    r"### Sentence \((?P<source_lang>[^)]+)\)\n\n```text\n"
    r"(?P<sentence_text>.*?)\n```",
    re.DOTALL,
)
JINJA_COMMENT_OR_BLOCK_PATTERN = re.compile(r"\{#.*?#\}|\{%.*?%\}", re.DOTALL)
JINJA_EXPR_PATTERN = re.compile(r"\{\{\s*(?P<expr>.*?)\s*\}\}", re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
HTML_BLOCK_END_PATTERN = re.compile(
    r"</(?:p|li|h[1-6]|dt|dd|th|td|caption)>|<br\s*/?>",
    re.IGNORECASE,
)
HTML_CONTEXT_BOUNDARY_PATTERN = re.compile(
    r"</(?:p|li|h[1-6]|dt|dd|th|td|caption|div|ul|ol|table|tr)>|<br\s*/?>",
    re.IGNORECASE,
)
INLINE_TRANSLATOR_TAGS = {"a", "em", "small", "span", "strong"}
INLINE_PLACEHOLDER_ELEMENT_PATTERN = re.compile(
    r"<(?P<tag>a|em|small|span|strong)\b[^>]*>"
    r".*?\{\{\s*(?P<expr>.*?)\s*\}\}.*?"
    r"</(?P=tag)>",
    re.DOTALL | re.IGNORECASE,
)
TRANSLATOR_PLACEHOLDER_PATTERN = re.compile(r"(?<!\{)\{(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\}(?!\})")
RAW_JINJA_IN_TRANSLATION_PATTERN = re.compile(r"\{[#%{]")
VISIBLE_TEXT_PATTERN = re.compile(r"[A-Za-z0-9]+")
CONNECTOR_ONLY_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
HARD_FRAGMENT_SENTENCES = {
    "available via:",
    "available with",
    "this data.",
    "this data are",
    "we will use.",
}
HARD_FRAGMENT_PREFIXES = (
    '" of this dataset',
    ", but decided ",
    ", legally",
    ", which",
    "and we will ",
    "but we won't ",
    'in order to "',
)
SENTENCE_TEXT_REPLACEMENTS = (
    (re.compile(r"\bbecauseit\b", re.IGNORECASE), "because it"),
    (re.compile(r"\blegaly\b", re.IGNORECASE), "legally"),
    (re.compile(r"\bdataare\b", re.IGNORECASE), "data are"),
    (re.compile(r"\bdatamay\b", re.IGNORECASE), "data may"),
    (re.compile(r"\busethe\b", re.IGNORECASE), "use the"),
    (re.compile(r"\buseonly\b", re.IGNORECASE), "use only"),
    (re.compile(r"\bwithfollowing\b", re.IGNORECASE), "with following"),
)


@dataclass(frozen=True)
class TranslationUnit:
    """One translator-facing unit captured from an expanded wrapper block."""

    source_file: str
    wrapper_name: str
    wrapper_order: int
    wrapper_key: str
    wrapper_folder_name: str
    wrapper_source_hash: str
    unit_order: int
    unit_key: str
    unit_folder_name: str
    unit_source_hash: str
    unit_start: int
    unit_end: int
    source_text: str


@dataclass(frozen=True)
class OutlineUnit:
    """One rendered outline row for a translator-facing unit."""

    source_file: str
    wrapper_order: int
    wrapper_folder_name: str
    unit_folder_name: str
    document_path: Path
    sentence_text: str
    is_translated: bool


@dataclass(frozen=True)
class TranslationEntry:
    """Translator-edited text plus the document it came from."""

    text: str
    document_path: str


@dataclass(frozen=True)
class TranslationTreeAuditIssue:
    """One machine-checkable issue in a translator-facing tree."""

    code: str
    location: str
    message: str


@dataclass(frozen=True)
class JinjaBranch:
    """One body inside an if/elif/else control group."""

    start: int
    end: int


@dataclass(frozen=True)
class JinjaBranchGroup:
    """One parsed Jinja if group with branch body offsets."""

    start: int
    end: int
    branches: tuple[JinjaBranch, ...]
    has_alternatives: bool


@dataclass(frozen=True)
class JinjaBranchRegions:
    """Split branch unit spans plus the control spans they came from."""

    units: tuple[AnnotationRegion, ...]
    covered: tuple[AnnotationRegion, ...]


class TranslationTreeError(RuntimeError):
    """Raised when the translator-facing tree is invalid."""


def export_translation_tree(
    *,
    source_dir: Path,
    output_dir: Path,
    source_lang: str = DEFAULT_SOURCE_LANG,
    target_lang: str = DEFAULT_TARGET_LANG,
) -> Path:
    """Export one expanded template workspace into translator-facing unit files."""

    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    _validate_expanded_workspace(source_dir)
    existing_translations = _load_existing_translations(
        output_dir=output_dir,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    _reset_dir(output_dir)
    tree_root = output_dir / TREE_ROOT_NAME
    tree_root.mkdir(parents=True, exist_ok=True)

    manifest_units: list[dict[str, str | int]] = []
    outline_units: list[OutlineUnit] = []

    for source_path in sorted(source_dir.rglob("*.j2")):
        relative_path = source_path.relative_to(source_dir)
        relative_posix = relative_path.as_posix()
        source_text = source_path.read_text(encoding="utf-8")
        units = _extract_units(relative_path=relative_posix, source_text=source_text)
        if not units:
            continue

        for unit in units:
            translation_text = existing_translations.get((unit.source_file, unit.unit_key), "")
            doc_dir = tree_root / relative_path / unit.wrapper_folder_name / unit.unit_folder_name
            doc_dir.mkdir(parents=True, exist_ok=True)
            document_path = doc_dir / TRANSLATION_DOC_NAME
            document_path.write_text(
                _render_translation_document(
                    unit=unit,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    translation_text=translation_text,
                ),
                encoding="utf-8",
            )
            manifest_units.append(
                {
                    "source_file": unit.source_file,
                    "wrapper_name": unit.wrapper_name,
                    "wrapper_order": unit.wrapper_order,
                    "wrapper_key": unit.wrapper_key,
                    "wrapper_folder_name": unit.wrapper_folder_name,
                    "wrapper_source_hash": unit.wrapper_source_hash,
                    "unit_order": unit.unit_order,
                    "unit_key": unit.unit_key,
                    "unit_folder_name": unit.unit_folder_name,
                    "unit_source_hash": unit.unit_source_hash,
                    "unit_start": unit.unit_start,
                    "unit_end": unit.unit_end,
                    "document_path": document_path.relative_to(output_dir).as_posix(),
                }
            )

            outline_units.append(
                OutlineUnit(
                    source_file=unit.source_file,
                    wrapper_order=unit.wrapper_order,
                    wrapper_folder_name=unit.wrapper_folder_name,
                    unit_folder_name=unit.unit_folder_name,
                    document_path=document_path,
                    sentence_text=_extract_sentence_text(unit.source_text),
                    is_translated=bool(translation_text.strip()),
                )
            )

    (output_dir / "README.md").write_text(
        _build_tree_readme(
            source_lang=source_lang,
            target_lang=target_lang,
        ),
        encoding="utf-8",
    )
    (output_dir / "outline.md").write_text(
        _render_outline_markdown(
            outline_units=outline_units,
            output_outline=output_dir / "outline.md",
        ),
        encoding="utf-8",
    )

    manifest_path = output_dir / TREE_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": TREE_VERSION,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "units": manifest_units,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_dir


def sync_translation_tree(
    *,
    tree_dir: Path,
    source_dir: Path,
    output_dir: Path,
    source_lang: str = DEFAULT_SOURCE_LANG,
    target_lang: str = DEFAULT_TARGET_LANG,
    template_organization_id: str | None = None,
    template_id: str | None = None,
    template_name: str | None = None,
    template_version: str | None = None,
) -> Path:
    """Apply translator-edited unit files back to one expanded workspace copy."""

    tree_dir = Path(tree_dir).resolve()
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    _validate_expanded_workspace(source_dir)
    manifest = _load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )

    translations = _load_translations_by_unit_key(
        tree_dir=tree_dir,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    units_by_file: dict[str, list[dict[str, str | int]]] = {}
    for unit in units:
        source_file = unit["source_file"]
        if not isinstance(source_file, str):
            raise TranslationTreeError(
                f"Invalid source_file in translation-tree manifest: {source_file!r}"
            )
        units_by_file.setdefault(source_file, []).append(unit)

    translated_files: dict[str, str] = {}
    for source_file, file_units in units_by_file.items():
        source_path = source_dir / source_file
        source_text = source_path.read_text(encoding="utf-8")
        wrapper_matches = list(GENERATED_BLOCK_PATTERN.finditer(source_text))

        units_by_wrapper: dict[int, list[dict[str, str | int]]] = {}
        for unit in file_units:
            wrapper_order = unit["wrapper_order"]
            if not isinstance(wrapper_order, int):
                raise TranslationTreeError(
                    f"Invalid wrapper_order in translation-tree manifest: {wrapper_order!r}"
                )
            units_by_wrapper.setdefault(wrapper_order, []).append(unit)

        rebuilt_parts: list[str] = []
        cursor = 0
        for wrapper_order, match in enumerate(wrapper_matches, start=1):
            rebuilt_parts.append(source_text[cursor : match.start()])

            wrapper_units = units_by_wrapper.get(wrapper_order)
            if not wrapper_units:
                rebuilt_parts.append(match.group(0))
                cursor = match.end()
                continue

            wrapper_name = generated_block_name(match)
            first_unit = wrapper_units[0]
            expected_wrapper_name = first_unit["wrapper_name"]
            if not isinstance(expected_wrapper_name, str) or wrapper_name != expected_wrapper_name:
                raise TranslationTreeError(
                    "Wrapper mismatch while syncing translation tree for "
                    f"{source_file}: expected {expected_wrapper_name}, found {wrapper_name}"
                )

            wrapper_body = generated_block_body(match)
            wrapper_hash = _hash_text(wrapper_body)
            expected_wrapper_hash = first_unit["wrapper_source_hash"]
            if not isinstance(expected_wrapper_hash, str) or wrapper_hash != expected_wrapper_hash:
                raise TranslationTreeError(
                    "Expanded source wrapper changed since the translation tree was exported for "
                    f"{source_file} ({first_unit['wrapper_folder_name']}). Re-run "
                    "`make export-translation-tree`."
                )

            rebuilt_parts.append(
                _wrap_translatable_block(
                    wrapper_name,
                    _apply_unit_translations(
                        source_file=source_file,
                        wrapper_body=wrapper_body,
                        wrapper_units=wrapper_units,
                        translations=translations,
                    ),
                )
            )
            cursor = match.end()

        unknown_wrapper_orders = [
            wrapper_order
            for wrapper_order in units_by_wrapper
            if wrapper_order < 1 or wrapper_order > len(wrapper_matches)
        ]
        if unknown_wrapper_orders:
            raise TranslationTreeError(
                "Translation tree references wrapper orders that do not exist in "
                f"{source_file}: {unknown_wrapper_orders}"
            )

        rebuilt_parts.append(source_text[cursor:])
        translated_files[source_file] = "".join(rebuilt_parts)

    _reset_dir(output_dir)
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)
    for source_file, translated_text in translated_files.items():
        (output_dir / source_file).write_text(translated_text, encoding="utf-8")
    _patch_template_metadata(
        output_dir=output_dir,
        organization_id=template_organization_id,
        template_id=template_id,
        name=template_name,
        version=template_version,
    )

    return output_dir


def audit_translation_tree(
    *,
    tree_dir: Path,
    source_dir: Path,
    source_lang: str = DEFAULT_SOURCE_LANG,
    target_lang: str = DEFAULT_TARGET_LANG,
) -> list[TranslationTreeAuditIssue]:
    """Return structural issues that make translation blocks unsafe to edit."""

    tree_dir = Path(tree_dir).resolve()
    source_dir = Path(source_dir).resolve()
    issues: list[TranslationTreeAuditIssue] = []

    try:
        _validate_expanded_workspace(source_dir)
    except TranslationTreeError as exc:
        return [
            TranslationTreeAuditIssue(
                code="invalid-expanded-workspace",
                location=str(source_dir),
                message=str(exc),
            )
        ]

    try:
        manifest = _load_tree_manifest(tree_dir)
    except TranslationTreeError as exc:
        return [
            TranslationTreeAuditIssue(
                code="invalid-translation-tree",
                location=str(tree_dir),
                message=str(exc),
            )
        ]

    units = manifest.get("units")
    if not isinstance(units, list):
        return [
            TranslationTreeAuditIssue(
                code="invalid-translation-tree",
                location=str(tree_dir / TREE_MANIFEST_PATH),
                message="Manifest `units` must be a list.",
            )
        ]

    for unit in units:
        issues.extend(
            _audit_manifest_unit(
                tree_dir=tree_dir,
                source_dir=source_dir,
                unit=unit,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        )

    return issues


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
        _validate_expanded_workspace(source_dir)
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


def _patch_template_metadata(
    *,
    output_dir: Path,
    organization_id: str | None,
    template_id: str | None,
    name: str | None,
    version: str | None,
) -> None:
    updates = {
        "organizationId": organization_id,
        "templateId": template_id,
        "name": name,
        "version": version,
    }
    updates = {key: value for key, value in updates.items() if value is not None}
    if not updates:
        return

    template_path = output_dir / "template.json"
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    for key, value in updates.items():
        payload[key] = value
    template_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


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
    source_text = source_path.read_text(encoding="utf-8")
    output_text = output_path.read_text(encoding="utf-8")
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
        if _literal_expr_to_text(expr) is not None:
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
    for token in _iter_executable_jinja_tokens(source_text):
        for match in JINJA_STRING_LITERAL_PATTERN.finditer(token):
            literal_value = _literal_match_value(match)
            if literal_value is None:
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


def _audit_manifest_unit(
    *,
    tree_dir: Path,
    source_dir: Path,
    unit: object,
    source_lang: str,
    target_lang: str,
) -> list[TranslationTreeAuditIssue]:
    issues: list[TranslationTreeAuditIssue] = []
    if not isinstance(unit, dict):
        return [
            TranslationTreeAuditIssue(
                code="invalid-manifest-unit",
                location=str(tree_dir / TREE_MANIFEST_PATH),
                message=f"Manifest unit must be an object, got {type(unit).__name__}.",
            )
        ]

    source_file = unit.get("source_file")
    unit_key = unit.get("unit_key")
    document_path_raw = unit.get("document_path")
    if not isinstance(source_file, str) or not isinstance(unit_key, str):
        return [
            TranslationTreeAuditIssue(
                code="invalid-manifest-unit",
                location=str(tree_dir / TREE_MANIFEST_PATH),
                message="Manifest unit is missing a valid source_file or unit_key.",
            )
        ]
    location = source_file if not isinstance(unit_key, str) else f"{source_file} ({unit_key})"

    try:
        source_unit_text = _source_unit_text_from_manifest_unit(
            source_dir=source_dir,
            unit=unit,
        )
    except TranslationTreeError as exc:
        issues.append(
            TranslationTreeAuditIssue(
                code="invalid-source-span",
                location=location,
                message=str(exc),
            )
        )
        source_unit_text = None

    if source_unit_text is not None:
        if _contains_jinja_block_or_comment(source_unit_text):
            issues.append(
                TranslationTreeAuditIssue(
                    code="unsafe-source-jinja-block",
                    location=location,
                    message=(
                        "Source unit contains raw Jinja block/comment syntax. "
                        "Expand/export must split this before translators edit it."
                    ),
                )
            )

        hard_fragment_message = _hard_fragment_sentence_message(source_unit_text)
        if hard_fragment_message is not None:
            issues.append(
                TranslationTreeAuditIssue(
                    code="hard-to-translate-source-fragment",
                    location=location,
                    message=hard_fragment_message,
                )
            )

        placeholder_map = _build_source_placeholder_map(source_unit_text)
        source_placeholder_names = set(_source_placeholder_counts(source_unit_text))
        ambiguous_names = sorted(source_placeholder_names - set(placeholder_map))
        if ambiguous_names:
            issues.append(
                TranslationTreeAuditIssue(
                    code="ambiguous-source-placeholder",
                    location=location,
                    message=(
                        "Source unit has placeholder names that cannot be mapped back "
                        f"unambiguously: {', '.join('{' + name + '}' for name in ambiguous_names)}"
                    ),
                )
            )

    if not isinstance(document_path_raw, str):
        issues.append(
            TranslationTreeAuditIssue(
                code="invalid-manifest-unit",
                location=location,
                message="Manifest unit is missing a valid document_path.",
            )
        )
        return issues

    document_path = tree_dir / document_path_raw
    if not document_path.is_file():
        issues.append(
            TranslationTreeAuditIssue(
                code="missing-translation-document",
                location=document_path_raw,
                message="Translation document is missing. Re-run export to restore it.",
            )
        )
        return issues

    try:
        translation_text = _parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
    except TranslationTreeError as exc:
        issues.append(
            TranslationTreeAuditIssue(
                code="invalid-translation-document",
                location=document_path_raw,
                message=str(exc),
            )
        )
        return issues

    has_raw_jinja_translation = _contains_raw_jinja_in_translation(translation_text)
    if has_raw_jinja_translation:
        issues.append(
            TranslationTreeAuditIssue(
                code="raw-jinja-in-translation",
                location=document_path_raw,
                message=(
                    "Translation block contains raw Jinja syntax. Use translator "
                    "placeholders such as `{name}` instead of `{% ... %}` or `{{ ... }}`."
                ),
            )
        )

    if source_unit_text is not None and translation_text.strip() and not has_raw_jinja_translation:
        try:
            _validate_translation_placeholders(
                source_file=source_file,
                unit_key=unit_key,
                translation_document_path=document_path_raw,
                source_text=source_unit_text,
                translation_text=translation_text,
            )
        except TranslationTreeError as exc:
            issues.append(
                TranslationTreeAuditIssue(
                    code="invalid-translation-placeholders",
                    location=document_path_raw,
                    message=str(exc),
                )
            )

    return issues


def _source_unit_text_from_manifest_unit(*, source_dir: Path, unit: dict) -> str:
    source_file = unit.get("source_file")
    wrapper_order = unit.get("wrapper_order")
    unit_start = unit.get("unit_start")
    unit_end = unit.get("unit_end")
    if (
        not isinstance(source_file, str)
        or not isinstance(wrapper_order, int)
        or not isinstance(unit_start, int)
        or not isinstance(unit_end, int)
    ):
        raise TranslationTreeError("Manifest unit has invalid source span metadata.")

    source_path = source_dir / source_file
    if not source_path.is_file():
        raise TranslationTreeError(f"Source file is missing: {source_path}")
    source_text = source_path.read_text(encoding="utf-8")
    wrappers = list(GENERATED_BLOCK_PATTERN.finditer(source_text))
    if wrapper_order < 1 or wrapper_order > len(wrappers):
        raise TranslationTreeError(
            f"Wrapper order {wrapper_order} does not exist in {source_file}."
        )
    wrapper_body = generated_block_body(wrappers[wrapper_order - 1])
    if unit_start < 0 or unit_end > len(wrapper_body) or unit_start >= unit_end:
        raise TranslationTreeError(
            f"Unit span {unit_start}:{unit_end} is invalid for {source_file}."
        )
    return wrapper_body[unit_start:unit_end]


def _extract_units(*, relative_path: str, source_text: str) -> list[TranslationUnit]:
    units: list[TranslationUnit] = []
    key_counts: dict[str, int] = {}

    for wrapper_index, match in enumerate(GENERATED_BLOCK_PATTERN.finditer(source_text), start=1):
        wrapper_name = generated_block_name(match)
        wrapper_body = generated_block_body(match)
        wrapper_key = _build_wrapper_key(relative_path=relative_path, source_text=wrapper_body)
        wrapper_folder_name = _build_folder_name(index=wrapper_index, slug=wrapper_key)
        wrapper_source_hash = _hash_text(wrapper_body)
        unit_regions = _extract_unit_regions(wrapper_body)

        unit_index = 0
        for region in unit_regions:
            unit_text = wrapper_body[region.start : region.end]
            if _is_unsafe_translation_unit_source(unit_text):
                continue
            if _is_connector_only_translation_unit(unit_text):
                continue
            unit_index += 1
            unit_key = _build_unit_key(
                relative_path=relative_path,
                wrapper_name=wrapper_name,
                source_text=unit_text,
            )
            key_counts[unit_key] = key_counts.get(unit_key, 0) + 1
            if key_counts[unit_key] > 1:
                unit_key = f"{unit_key}-{key_counts[unit_key]}"
            unit_folder_name = _build_folder_name(index=unit_index, slug=unit_key)
            units.append(
                TranslationUnit(
                    source_file=relative_path,
                    wrapper_name=wrapper_name,
                    wrapper_order=wrapper_index,
                    wrapper_key=wrapper_key,
                    wrapper_folder_name=wrapper_folder_name,
                    wrapper_source_hash=wrapper_source_hash,
                    unit_order=unit_index,
                    unit_key=unit_key,
                    unit_folder_name=unit_folder_name,
                    unit_source_hash=_hash_text(unit_text),
                    unit_start=region.start,
                    unit_end=region.end,
                    source_text=unit_text,
                )
            )

    return units


def _extract_unit_regions(wrapper_body: str) -> list[AnnotationRegion]:
    if not wrapper_body.strip():
        return []

    tokens = _lex_source_tokens(wrapper_body)
    outer_bounds = _find_single_outer_element_inner_bounds(tokens=tokens)
    if outer_bounds is not None:
        inner_start, inner_end = outer_bounds
        inner_text = wrapper_body[inner_start:inner_end]
        if _should_keep_single_outer_element(wrapper_body=wrapper_body, inner_text=inner_text):
            return [AnnotationRegion(start=0, end=len(wrapper_body))]
        inner_regions = _collect_translation_unit_regions(inner_text)
        normalized_inner_regions = _normalize_regions(
            regions=inner_regions,
            source_text=wrapper_body,
            base_offset=inner_start,
        )
        if normalized_inner_regions:
            return _merge_inline_expression_split_regions(
                regions=normalized_inner_regions,
                source_text=wrapper_body,
            )

    normalized_regions = _normalize_regions(
        regions=_collect_translation_unit_regions(wrapper_body),
        source_text=wrapper_body,
        base_offset=0,
    )
    if normalized_regions:
        return _merge_inline_expression_split_regions(
            regions=normalized_regions,
            source_text=wrapper_body,
        )

    return [AnnotationRegion(start=0, end=len(wrapper_body))]


def _merge_inline_expression_split_regions(
    *,
    regions: list[AnnotationRegion],
    source_text: str,
) -> list[AnnotationRegion]:
    """Repair regions split only by a placeholder inside one sentence."""

    merged: list[AnnotationRegion] = []
    for region in regions:
        if not merged:
            merged.append(region)
            continue

        previous = merged[-1]
        candidate = AnnotationRegion(start=previous.start, end=region.end)
        if _should_merge_inline_expression_split(
            left=source_text[previous.start : previous.end],
            gap=source_text[previous.end : region.start],
            combined=source_text[candidate.start : candidate.end],
        ):
            merged[-1] = candidate
        else:
            merged.append(region)
    return merged


def _should_merge_inline_expression_split(*, left: str, gap: str, combined: str) -> bool:
    if not gap.strip():
        return False
    gap_tokens = _lex_source_tokens(gap)
    if not gap_tokens or not any(token.kind == "jinja_expr" for token in gap_tokens):
        return False
    if any(token.kind in {"html_tag", "jinja_block", "jinja_comment"} for token in gap_tokens):
        return False
    if _contains_jinja_block_or_comment(combined):
        return False

    left_sentence = _extract_sentence_text(left)
    combined_sentence = _extract_sentence_text(combined)
    if _ends_with_sentence_punctuation(left_sentence):
        return False
    return _ends_with_sentence_punctuation(combined_sentence)


def _ends_with_sentence_punctuation(sentence: str) -> bool:
    return sentence.rstrip(")]}\"'»”").endswith((".", "!", "?", ":"))


def _should_keep_single_outer_element(*, wrapper_body: str, inner_text: str) -> bool:
    """Keep simple inline-markup sentences together instead of splitting at tags."""

    if not _contains_translatable_text(wrapper_body):
        return False
    tokens = _lex_source_tokens(inner_text)
    has_inline_markup = any(
        token.kind == "html_tag" and token.tag_name in {"a", "em", "small", "span", "strong"}
        for token in tokens
    )
    has_dynamic_expression = any(token.kind in {"jinja_expr", "jinja_comment"} for token in tokens)
    has_control_block = any(token.kind == "jinja_block" for token in tokens)
    return has_inline_markup and not has_dynamic_expression and not has_control_block


def _contains_machine_only_inline_markup(source_text: str) -> bool:
    """Avoid merging hidden formatter calls into one visible translation unit."""

    tokens = _lex_source_tokens(source_text)
    has_inline_markup = any(
        token.kind == "html_tag" and token.tag_name in {"a", "em", "small", "span", "strong"}
        for token in tokens
    )
    if not has_inline_markup:
        return False
    for match in JINJA_EXPR_PATTERN.finditer(source_text):
        expr = " ".join(match.group("expr").strip().split())
        if "(" in expr:
            return True
    return False


def _collect_translation_unit_regions(source_text: str) -> list[AnnotationRegion]:
    tokens = _lex_source_tokens(source_text)
    branch_region_set = _collect_branch_unit_regions(source_text)
    branch_regions = list(branch_region_set.units)
    branch_covered_regions = list(branch_region_set.covered)
    element_regions = [
        region
        for region in _collect_leaf_element_regions(tokens=tokens, source_text=source_text)
        if not _overlaps_any_region(region=region, regions=branch_covered_regions)
    ]
    inline_regions = _collect_inline_text_regions(
        tokens=tokens,
        source_text=source_text,
        covered_regions=branch_covered_regions + element_regions,
    )
    literal_regions = _collect_jinja_literal_regions(
        tokens=tokens,
        source_text=source_text,
        covered_regions=branch_covered_regions + element_regions + inline_regions,
    )
    return sorted(
        branch_regions + element_regions + inline_regions + literal_regions,
        key=lambda item: item.start,
    )


def _collect_branch_unit_regions(source_text: str, *, base_offset: int = 0) -> JinjaBranchRegions:
    regions: list[AnnotationRegion] = []
    covered_regions: list[AnnotationRegion] = []
    tokens = _lex_source_tokens(source_text)

    for group in _collect_jinja_if_groups(tokens=tokens):
        group_units: list[AnnotationRegion] = []
        group_covered_regions: list[AnnotationRegion] = []
        group_has_units = False
        all_branches_are_represented = True

        for branch in group.branches:
            branch_text = source_text[branch.start : branch.end]
            nested_regions = _collect_branch_unit_regions(
                branch_text,
                base_offset=base_offset + branch.start,
            )
            if nested_regions.units:
                group_has_units = True
                regions.extend(nested_regions.units)
                covered_regions.extend(nested_regions.covered)
                local_nested_covered = [
                    AnnotationRegion(
                        start=region.start - base_offset - branch.start,
                        end=region.end - base_offset - branch.start,
                    )
                    for region in nested_regions.covered
                ]
                outside_regions = _collect_regions_outside_covered(
                    source_text=branch_text,
                    covered_regions=local_nested_covered,
                )
                for outside_region in outside_regions:
                    absolute_region = AnnotationRegion(
                        start=base_offset + branch.start + outside_region.start,
                        end=base_offset + branch.start + outside_region.end,
                    )
                    regions.append(absolute_region)
                    covered_regions.append(absolute_region)
                    group_covered_regions.append(absolute_region)

                represented_regions = [*local_nested_covered, *outside_regions]
                if _contains_translatable_text_outside_regions(
                    source_text=branch_text,
                    covered_regions=represented_regions,
                ):
                    all_branches_are_represented = False
                continue

            local_control_groups = _collect_jinja_if_groups(tokens=_lex_source_tokens(branch_text))
            local_machine_control_regions = [
                AnnotationRegion(start=control_group.start, end=control_group.end)
                for control_group in local_control_groups
                if not _contains_translatable_text(
                    branch_text[control_group.start : control_group.end]
                )
            ]
            if local_machine_control_regions:
                outside_regions = _collect_regions_outside_covered(
                    source_text=branch_text,
                    covered_regions=local_machine_control_regions,
                )
                for outside_region in outside_regions:
                    absolute_region = AnnotationRegion(
                        start=base_offset + branch.start + outside_region.start,
                        end=base_offset + branch.start + outside_region.end,
                    )
                    regions.append(absolute_region)
                    covered_regions.append(absolute_region)
                    group_covered_regions.append(absolute_region)
                    group_has_units = True
                represented_regions = [*local_machine_control_regions, *outside_regions]
                if not _contains_translatable_text_outside_regions(
                    source_text=branch_text,
                    covered_regions=represented_regions,
                ):
                    continue

            if _starts_with_sentence_prefix_punctuation(branch_text):
                all_branches_are_represented = False
                continue
            if not _is_simple_branch_translation_unit(branch_text):
                all_branches_are_represented = False
                continue
            if not group.has_alternatives and not _is_complete_standalone_unit(branch_text):
                all_branches_are_represented = False
                continue

            local_region = _normalize_region(
                AnnotationRegion(start=branch.start, end=branch.end),
                source_text=source_text,
                base_offset=0,
            )
            if local_region is not None and _contains_translatable_text(
                source_text[branch.start : branch.end]
            ):
                group_has_units = True
                group_units.append(
                    AnnotationRegion(
                        start=base_offset + local_region.start,
                        end=base_offset + local_region.end,
                    )
                )
                group_covered_regions.append(
                    AnnotationRegion(
                        start=base_offset + local_region.start,
                        end=base_offset + local_region.end,
                    )
                )
            else:
                group_covered_regions.append(
                    AnnotationRegion(
                        start=base_offset + branch.start,
                        end=base_offset + branch.end,
                    )
                )

        regions.extend(group_units)
        if group_has_units:
            if group.has_alternatives and all_branches_are_represented:
                covered_regions.append(
                    AnnotationRegion(
                        start=base_offset + group.start,
                        end=base_offset + group.end,
                    )
                )
            else:
                covered_regions.extend(group_covered_regions)

    return JinjaBranchRegions(
        units=tuple(_dedupe_regions(regions)),
        covered=tuple(_dedupe_regions(covered_regions)),
    )


def _collect_jinja_if_groups(*, tokens: list[SourceToken]) -> list[JinjaBranchGroup]:
    groups: list[JinjaBranchGroup] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "jinja_block" and _jinja_block_keyword(token.text) == "if":
            parsed_group, end_index = _parse_jinja_if_group(tokens=tokens, start_index=index)
            if parsed_group is not None:
                groups.append(parsed_group)
                index = end_index + 1
                continue
        index += 1
    return groups


def _parse_jinja_if_group(
    *, tokens: list[SourceToken], start_index: int
) -> tuple[JinjaBranchGroup | None, int]:
    start_token = tokens[start_index]
    depth = 1
    branch_start = start_token.end
    branches: list[JinjaBranch] = []
    has_elif_or_else = False

    for index in range(start_index + 1, len(tokens)):
        token = tokens[index]
        if token.kind != "jinja_block":
            continue
        keyword = _jinja_block_keyword(token.text)
        if keyword == "if":
            depth += 1
            continue
        if keyword == "endif":
            depth -= 1
            if depth == 0:
                branches.append(JinjaBranch(start=branch_start, end=token.start))
                return (
                    JinjaBranchGroup(
                        start=start_token.start,
                        end=token.end,
                        branches=tuple(branches),
                        has_alternatives=has_elif_or_else,
                    ),
                    index,
                )
            continue
        if depth == 1 and keyword in {"elif", "else"}:
            has_elif_or_else = True
            branches.append(JinjaBranch(start=branch_start, end=token.start))
            branch_start = token.end

    return None, start_index


def _jinja_block_keyword(token_text: str) -> str:
    inner = token_text[2:-2].strip().strip("-").strip()
    return inner.split(None, 1)[0] if inner else ""


def _is_branch_group_locally_safe(*, source_text: str, group: JinjaBranchGroup) -> bool:
    """Only split branch groups that are not glued to a partial surrounding sentence."""

    return _has_safe_left_boundary(source_text[: group.start]) and _has_safe_right_boundary(
        source_text[group.end :]
    )


def _is_simple_branch_translation_unit(source_text: str) -> bool:
    """Avoid turning whole list/table branches into one huge translation unit."""

    tokens = _lex_source_tokens(source_text)
    structural_keywords = {"for", "endfor", "elif", "else", "macro", "endmacro"}
    if any(
        token.kind == "jinja_block" and _jinja_block_keyword(token.text) in structural_keywords
        for token in tokens
    ):
        return False
    if any(group.has_alternatives for group in _collect_jinja_if_groups(tokens=tokens)):
        return False

    block_tags = {
        "blockquote",
        "dd",
        "div",
        "dl",
        "dt",
        "li",
        "ol",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
    return not any(token.kind == "html_tag" and token.tag_name in block_tags for token in tokens)


def _is_complete_standalone_unit(source_text: str) -> bool:
    """Allow optional `if` bodies only when they are complete translator units."""

    sentence = _extract_sentence_text(source_text)
    if not re.search(r"[A-Za-z0-9]", sentence):
        return False
    if sentence.startswith((",", ".", ";", ":")):
        return False
    return sentence.endswith((".", "!", "?", ":"))


def _starts_with_sentence_prefix_punctuation(source_text: str) -> bool:
    visible = _visible_context_text(source_text)
    return bool(visible) and visible[0] in ".,;:"


def _has_safe_left_boundary(prefix: str) -> bool:
    visible = _visible_left_context_text(prefix)
    if not visible:
        return True
    return visible[-1] in ".!?:;)]"


def _has_safe_right_boundary(suffix: str) -> bool:
    visible = _visible_right_context_text(suffix)
    if not visible:
        return True
    return visible[0] in ".!?:;,)]}" or visible[0].isupper()


def _visible_context_text(source_text: str) -> str:
    stripped = JINJA_EXPR_PATTERN.sub(" {value} ", source_text)
    stripped = JINJA_COMMENT_OR_BLOCK_PATTERN.sub(" ", stripped)
    stripped = HTML_TAG_PATTERN.sub(" ", stripped)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def _visible_left_context_text(prefix: str) -> str:
    parts = HTML_CONTEXT_BOUNDARY_PATTERN.split(prefix)
    return _visible_context_text(parts[-1] if parts else prefix)


def _visible_right_context_text(suffix: str) -> str:
    match = HTML_CONTEXT_BOUNDARY_PATTERN.search(suffix)
    if match is None:
        return _visible_context_text(suffix)
    return _visible_context_text(suffix[: match.start()])


def _overlaps_any_region(*, region: AnnotationRegion, regions: list[AnnotationRegion]) -> bool:
    return any(region.start < other.end and other.start < region.end for other in regions)


def _contains_translatable_text_outside_regions(
    *, source_text: str, covered_regions: list[AnnotationRegion]
) -> bool:
    cursor = 0
    for region in sorted(covered_regions, key=lambda item: item.start):
        if region.start > cursor and _contains_translatable_text(
            source_text[cursor : region.start]
        ):
            return True
        cursor = max(cursor, region.end)
    return cursor < len(source_text) and _contains_translatable_text(source_text[cursor:])


def _collect_regions_outside_covered(
    *, source_text: str, covered_regions: list[AnnotationRegion]
) -> list[AnnotationRegion]:
    tokens = _lex_source_tokens(source_text)
    leaf_regions = [
        region
        for region in _collect_leaf_element_regions(tokens=tokens, source_text=source_text)
        if not _overlaps_any_region(region=region, regions=covered_regions)
    ]
    inline_regions = _collect_inline_text_regions(
        tokens=tokens,
        source_text=source_text,
        covered_regions=[*covered_regions, *leaf_regions],
        include_control_tokens=False,
    )
    return _normalize_regions(
        regions=[*leaf_regions, *inline_regions],
        source_text=source_text,
        base_offset=0,
    )


def _collect_jinja_literal_regions(
    *,
    tokens: list[SourceToken],
    source_text: str,
    covered_regions: list[AnnotationRegion],
) -> list[AnnotationRegion]:
    regions: list[AnnotationRegion] = []
    for token in tokens:
        if token.kind not in {"jinja_block", "jinja_expr"}:
            continue
        if _is_inside_region(token=token, regions=covered_regions):
            continue
        if token.kind == "jinja_block" and not _extract_translatable_jinja_block_literals(
            token.text[2:-2]
        ):
            continue
        for match in JINJA_STRING_LITERAL_PATTERN.finditer(token.text):
            literal = match.group("literal")
            if _is_subscript_literal(expr=token.text, start=match.start(), end=match.end()):
                continue
            if _is_dict_key_literal(expr=token.text, end=match.end()):
                continue
            try:
                value = ast.literal_eval(literal)
            except (SyntaxError, ValueError):
                continue
            if not isinstance(value, str) or not _is_translatable_jinja_literal(value):
                continue
            literal_start = token.start + match.start("literal") + 1
            literal_end = token.start + match.end("literal") - 1
            region = AnnotationRegion(start=literal_start, end=literal_end)
            if _overlaps_any_region(region=region, regions=covered_regions):
                continue
            if _contains_translatable_text(source_text[literal_start:literal_end]):
                regions.append(region)
    return _dedupe_regions(regions)


def _dedupe_regions(regions: list[AnnotationRegion]) -> list[AnnotationRegion]:
    # Prefer the widest region for the same start. Otherwise a raw text fragment
    # such as "Starting" can hide the richer branch unit "Starting {{ date }}:".
    unique = sorted(set(regions), key=lambda item: (item.start, -item.end))
    deduped: list[AnnotationRegion] = []
    for region in unique:
        if deduped and _overlaps_any_region(region=region, regions=[deduped[-1]]):
            continue
        deduped.append(region)
    return deduped


def _collect_leaf_element_regions(
    *, tokens: list[SourceToken], source_text: str
) -> list[AnnotationRegion]:
    candidate_regions: list[AnnotationRegion] = []
    for index, token in enumerate(tokens):
        if (
            token.kind == "html_tag"
            and token.is_opening_tag
            and not token.is_self_closing_tag
            and token.tag_name in ANNOTATABLE_HTML_TAGS
        ):
            end_index = _find_matching_tag_end(tokens=tokens, start_index=index)
            if end_index is None:
                continue
            region = AnnotationRegion(start=token.start, end=tokens[end_index].end)
            region_text = source_text[region.start : region.end]
            if _contains_translatable_text(region_text) and not (
                _contains_machine_only_inline_markup(region_text)
                or _contains_jinja_block_or_comment(region_text)
            ):
                candidate_regions.append(region)

    leaf_regions: list[AnnotationRegion] = []
    for region in candidate_regions:
        contains_child = any(
            other.start > region.start and other.end < region.end for other in candidate_regions
        )
        if not contains_child:
            leaf_regions.append(region)
    return leaf_regions


def _collect_inline_text_regions(
    *,
    tokens: list[SourceToken],
    source_text: str,
    covered_regions: list[AnnotationRegion],
    include_control_tokens: bool = False,
) -> list[AnnotationRegion]:
    regions: list[AnnotationRegion] = []
    pending_tokens: list[SourceToken] = []

    def flush_pending() -> None:
        nonlocal pending_tokens
        if not pending_tokens:
            return
        start = pending_tokens[0].start
        end = pending_tokens[-1].end
        raw_text = source_text[start:end]
        if _contains_translatable_text(raw_text):
            regions.append(AnnotationRegion(start=start, end=end))
        pending_tokens = []

    for token in tokens:
        if _is_inside_region(token=token, regions=covered_regions):
            flush_pending()
            continue
        # Raw Jinja control blocks are executable template code, not translator text.
        # Expanded rewrites should duplicate safe branch sentences instead of asking
        # translators to preserve `{% ... %}` manually.
        is_translator_visible_jinja_expr = (
            token.kind == "jinja_expr" and _is_translator_visible_jinja_expr(token.text)
        )
        if (
            token.kind == "html_tag"
            and token.tag_name in INLINE_TRANSLATOR_TAGS
            or token.kind in {"text", "jinja_comment"}
            or is_translator_visible_jinja_expr
        ) or (include_control_tokens and token.kind == "jinja_block"):
            pending_tokens.append(token)
            continue
        flush_pending()

    flush_pending()
    return regions


def _is_translator_visible_jinja_expr(token_text: str) -> bool:
    match = JINJA_EXPR_PATTERN.fullmatch(token_text)
    if match is None:
        return True
    expr = match.group("expr").strip()
    if _literal_expr_to_text(expr) is not None:
        return True
    return not _extract_translatable_jinja_literals(expr)


def _is_inside_region(*, token: SourceToken, regions: list[AnnotationRegion]) -> bool:
    return any(region.start <= token.start and token.end <= region.end for region in regions)


def _find_single_outer_element_inner_bounds(*, tokens: list[SourceToken]) -> tuple[int, int] | None:
    element = _find_single_outer_element(tokens=tokens)
    if element is None:
        return None
    return (element[1], element[2])


def _find_single_outer_element(*, tokens: list[SourceToken]) -> tuple[str, int, int] | None:
    first_index = _find_first_meaningful_token_index(tokens)
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

    if any(not _is_ignorable_outer_token(token) for token in tokens[:first_index]):
        return None
    if any(not _is_ignorable_outer_token(token) for token in tokens[end_index + 1 :]):
        return None

    return (first_token.tag_name or "", first_token.end, end_token.start)


def _find_first_meaningful_token_index(tokens: list[SourceToken]) -> int | None:
    for index, token in enumerate(tokens):
        if not _is_ignorable_outer_token(token):
            return index
    return None


def _is_ignorable_outer_token(token: SourceToken) -> bool:
    if token.kind == "jinja_comment":
        return True
    if token.kind == "text" and not token.text.strip():
        return True
    return False


def _normalize_regions(
    *,
    regions: list[AnnotationRegion],
    source_text: str,
    base_offset: int,
) -> list[AnnotationRegion]:
    normalized: list[AnnotationRegion] = []
    for region in sorted(regions, key=lambda item: item.start):
        normalized_region = _normalize_region(
            region,
            source_text=source_text,
            base_offset=base_offset,
        )
        if normalized_region is None:
            continue
        normalized.append(normalized_region)
    return _dedupe_regions(normalized)


def _normalize_region(
    region: AnnotationRegion,
    *,
    source_text: str,
    base_offset: int,
) -> AnnotationRegion | None:
    start = base_offset + region.start
    end = base_offset + region.end
    while start < end and source_text[start].isspace():
        start += 1
    while end > start and source_text[end - 1].isspace():
        end -= 1
    start, end = _trim_non_rendering_edge_tokens(source_text=source_text, start=start, end=end)
    if start >= end:
        return None
    if not _contains_translatable_text(source_text[start:end]):
        return None
    return AnnotationRegion(start=start, end=end)


def _trim_non_rendering_edge_tokens(*, source_text: str, start: int, end: int) -> tuple[int, int]:
    tokens = [
        token for token in _lex_source_tokens(source_text[start:end]) if token.end > token.start
    ]
    left = 0
    right = len(tokens)
    while left < right and _is_non_rendering_edge_token(tokens[left]):
        left += 1
    while right > left and _is_non_rendering_edge_token(tokens[right - 1]):
        right -= 1
    if left >= right:
        return start, start
    return start + tokens[left].start, start + tokens[right - 1].end


def _is_non_rendering_edge_token(token: SourceToken) -> bool:
    if token.kind == "text":
        return not token.text.strip()
    if token.kind == "jinja_comment":
        return True
    if token.kind != "jinja_block":
        return False
    inner = token.text[2:-2].strip().strip("-").strip()
    if _extract_translatable_jinja_block_literals(inner):
        return False
    return _jinja_block_keyword(token.text) in {"set", "do"}


def _apply_unit_translations(
    *,
    source_file: str,
    wrapper_body: str,
    wrapper_units: list[dict[str, str | int]],
    translations: dict[tuple[str, str], TranslationEntry],
) -> str:
    rebuilt_parts: list[str] = []
    cursor = 0
    sorted_units = sorted(
        wrapper_units,
        key=lambda unit: (
            int(unit["unit_start"]),
            int(unit["unit_end"]),
        ),
    )

    for unit in sorted_units:
        unit_start = unit["unit_start"]
        unit_end = unit["unit_end"]
        unit_key = unit["unit_key"]
        unit_source_hash = unit["unit_source_hash"]
        if not isinstance(unit_start, int) or not isinstance(unit_end, int):
            raise TranslationTreeError(
                f"Invalid unit offsets in translation-tree manifest for {source_file}"
            )
        if not isinstance(unit_key, str) or not isinstance(unit_source_hash, str):
            raise TranslationTreeError(
                f"Invalid unit metadata in translation-tree manifest for {source_file}"
            )
        if unit_start < cursor or unit_end > len(wrapper_body) or unit_start >= unit_end:
            raise TranslationTreeError(
                f"Invalid unit span for {source_file} ({unit_key}): {unit_start}:{unit_end}"
            )

        source_unit_text = wrapper_body[unit_start:unit_end]
        current_unit_hash = _hash_text(source_unit_text)
        if current_unit_hash != unit_source_hash:
            raise TranslationTreeError(
                "Expanded source unit changed since the translation tree was exported for "
                f"{source_file} ({unit_key}). Re-run `make export-translation-tree`."
            )

        rebuilt_parts.append(wrapper_body[cursor:unit_start])
        translation_entry = translations.get((source_file, unit_key))
        if translation_entry is not None and translation_entry.text.strip():
            translation_text = translation_entry.text
            _validate_translation_placeholders(
                source_file=source_file,
                unit_key=unit_key,
                translation_document_path=(
                    translation_entry.document_path if translation_entry is not None else None
                ),
                source_text=source_unit_text,
                translation_text=translation_text,
            )
            translation_text = _materialize_translation_placeholders(
                source_text=source_unit_text,
                translation_text=translation_text,
            )
            translation_text = _preserve_single_outer_element(
                source_text=source_unit_text,
                translation_text=translation_text,
            )
        else:
            translation_text = source_unit_text
        rebuilt_parts.append(translation_text)
        cursor = unit_end

    rebuilt_parts.append(wrapper_body[cursor:])
    return "".join(rebuilt_parts)


def _validate_translation_placeholders(
    *,
    source_file: str,
    unit_key: str,
    translation_document_path: str | None,
    source_text: str,
    translation_text: str,
) -> None:
    if _contains_raw_jinja_in_translation(translation_text):
        location = _format_translation_location(
            source_file,
            unit_key,
            translation_document_path,
        )
        raise TranslationTreeError(
            "Translation contains raw Jinja syntax for "
            f"{location}. Use translator placeholders such as `{{name}}` instead."
        )

    source_counts = _source_placeholder_counts(source_text)
    if not source_counts and not _extract_translator_placeholder_names(translation_text):
        return

    placeholder_map = _build_source_placeholder_map(source_text)
    shorthand_names = _extract_translator_placeholder_names(translation_text)
    unknown_shorthand_names = sorted(set(shorthand_names) - set(placeholder_map))
    if unknown_shorthand_names:
        formatted_names = ", ".join(f"{{{name}}}" for name in unknown_shorthand_names)
        location = _format_translation_location(
            source_file,
            unit_key,
            translation_document_path,
        )
        raise TranslationTreeError(
            "Translation uses placeholder names that cannot be mapped back to Jinja "
            f"for {location}: {formatted_names}"
        )

    translation_counts = _translation_placeholder_counts(translation_text)
    unexpected_placeholder_names = sorted(set(translation_counts) - set(source_counts))
    if unexpected_placeholder_names:
        formatted_names = ", ".join(f"{{{name}}}" for name in unexpected_placeholder_names)
        location = _format_translation_location(
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
        location = _format_translation_location(
            source_file,
            unit_key,
            translation_document_path,
        )
        raise TranslationTreeError(
            f"Translation is missing required placeholders for {location}: {formatted_names}"
        )


def _format_translation_location(
    source_file: str,
    unit_key: str,
    translation_document_path: str | None,
) -> str:
    location = f"{source_file} ({unit_key})"
    if translation_document_path:
        location = f"{location} in {translation_document_path}"
    return location


def _source_placeholder_counts(source_text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for match in JINJA_EXPR_PATTERN.finditer(_visible_placeholder_source_text(source_text)):
        for name in _extract_translator_placeholder_names(
            _jinja_expr_to_placeholder(match.group("expr"))
        ):
            counts[name] += 1
    return counts


def _translation_placeholder_counts(translation_text: str) -> Counter[str]:
    counts: Counter[str] = Counter(_extract_translator_placeholder_names(translation_text))
    for match in JINJA_EXPR_PATTERN.finditer(translation_text):
        for name in _extract_translator_placeholder_names(
            _jinja_expr_to_placeholder(match.group("expr"))
        ):
            counts[name] += 1
    return counts


def _build_source_placeholder_map(source_text: str) -> dict[str, str]:
    expressions_by_name: dict[str, set[str]] = {}
    for match in JINJA_EXPR_PATTERN.finditer(_visible_placeholder_source_text(source_text)):
        expression = " ".join(match.group("expr").strip().split())
        placeholder_names = _extract_translator_placeholder_names(
            _jinja_expr_to_placeholder(match.group("expr"))
        )
        for name in placeholder_names:
            expressions_by_name.setdefault(name, set()).add(expression)
    return {
        name: next(iter(expressions))
        for name, expressions in expressions_by_name.items()
        if len(expressions) == 1
    }


def _extract_translator_placeholder_names(source_text: str) -> list[str]:
    return [match.group("name") for match in TRANSLATOR_PLACEHOLDER_PATTERN.finditer(source_text)]


def _materialize_translation_placeholders(*, source_text: str, translation_text: str) -> str:
    placeholder_map = _build_source_placeholder_map(source_text)

    def replace_placeholder(match: re.Match[str]) -> str:
        name = match.group("name")
        expression = placeholder_map.get(name)
        if expression is None:
            return match.group(0)
        return "{{ " + expression + " }}"

    return TRANSLATOR_PLACEHOLDER_PATTERN.sub(replace_placeholder, translation_text)


def _visible_placeholder_source_text(source_text: str) -> str:
    """Return source text that translators can actually see and rearrange.

    Attribute-only Jinja expressions such as ``href="{{ url }}"`` are machine
    wiring. They must not force translators to duplicate placeholders that are
    already visible inside the link text.
    """

    return HTML_TAG_PATTERN.sub(" ", source_text)


def _preserve_single_outer_element(*, source_text: str, translation_text: str) -> str:
    """Keep simple structural tags when translators provide text-only content."""

    if HTML_TAG_PATTERN.search(translation_text):
        return translation_text

    tokens = _lex_source_tokens(source_text)
    outer_element = _find_single_outer_element(tokens=tokens)
    if outer_element is None:
        outer_element = _find_single_outer_inline_element(tokens=tokens)
    outer_tag = outer_element[0] if outer_element is not None else ""
    if outer_tag not in INLINE_TRANSLATOR_TAGS:
        translation_text = _preserve_inline_placeholder_elements(
            source_text=source_text,
            translation_text=translation_text,
        )
        translation_text = _preserve_single_inner_inline_element(
            source_text=source_text,
            translation_text=translation_text,
        )

    if outer_element is None:
        return translation_text

    _, inner_start, inner_end = outer_element
    return source_text[:inner_start] + translation_text + source_text[inner_end:]


def _preserve_single_inner_inline_element(*, source_text: str, translation_text: str) -> str:
    """Keep a single inline child such as ``<p><em>...</em></p>`` intact."""

    tokens = _lex_source_tokens(source_text)
    outer_element = _find_single_outer_element(tokens=tokens)
    if outer_element is None:
        return translation_text

    _, inner_start, inner_end = outer_element
    inner_source = source_text[inner_start:inner_end]
    inner_tokens = _lex_source_tokens(inner_source)
    inner_element = _find_single_outer_inline_element(tokens=inner_tokens)
    if inner_element is None:
        return translation_text

    _, inline_inner_start, inline_inner_end = inner_element
    if _contains_jinja_block_or_comment(inner_source):
        return translation_text

    return inner_source[:inline_inner_start] + translation_text + inner_source[inline_inner_end:]


def _find_single_outer_inline_element(
    *,
    tokens: list[SourceToken],
) -> tuple[str, int, int] | None:
    first_index = _find_first_meaningful_token_index(tokens)
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

    if any(not _is_ignorable_outer_token(token) for token in tokens[:first_index]):
        return None
    if any(not _is_ignorable_outer_token(token) for token in tokens[end_index + 1 :]):
        return None

    return (first_token.tag_name or "", first_token.end, end_token.start)


def _preserve_inline_placeholder_elements(*, source_text: str, translation_text: str) -> str:
    """Restore inline source markup that only wraps one visible placeholder.

    Translators usually should not edit HTML. When they provide text-only
    translations, source links such as ``<a href="{{ pid }}">{{ pid }}</a>``
    still need to survive because the href is machine wiring, not prose.
    """

    restored_text = translation_text
    for match in INLINE_PLACEHOLDER_ELEMENT_PATTERN.finditer(source_text):
        inline_source = match.group(0)
        if _contains_jinja_block_or_comment(inline_source):
            continue

        expression = " ".join(match.group("expr").strip().split())
        visible_inner = HTML_TAG_PATTERN.sub("", inline_source)
        visible_inner = re.sub(r"\s+", " ", visible_inner).strip()
        if visible_inner != "{{ " + expression + " }}":
            continue

        placeholder = "{{ " + expression + " }}"
        restored_text = restored_text.replace(placeholder, inline_source, 1)
    return restored_text


def _build_wrapper_key(*, relative_path: str, source_text: str) -> str:
    visible_text = _extract_visible_text(source_text)
    slug = _slugify_text(visible_text)
    return f"{slug}-{_hash_text(relative_path + '|' + source_text)[:10]}"


def _build_unit_key(*, relative_path: str, wrapper_name: str, source_text: str) -> str:
    visible_text = _extract_visible_text(source_text)
    slug = _slugify_text(visible_text)
    return f"{slug}-{_hash_text(relative_path + '|' + wrapper_name + '|' + source_text)[:10]}"


def _build_folder_name(*, index: int, slug: str) -> str:
    return f"{index:04d}-{slug}"


def _extract_visible_text(source_text: str) -> str:
    stripped = JINJA_EXPR_PATTERN.sub(_replace_expr_with_visible_literals, source_text)
    stripped = JINJA_COMMENT_OR_BLOCK_PATTERN.sub(_replace_block_with_visible_literals, stripped)
    stripped = HTML_TAG_PATTERN.sub(" ", stripped)
    stripped = html.unescape(stripped)
    words = VISIBLE_TEXT_PATTERN.findall(stripped)
    if not words:
        return "unit"
    return " ".join(words[:8])


def _slugify_text(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unit"


def _contains_translatable_text(source_text: str) -> bool:
    stripped = JINJA_EXPR_PATTERN.sub(_replace_expr_with_visible_literals, source_text)
    stripped = JINJA_COMMENT_OR_BLOCK_PATTERN.sub(_replace_block_with_visible_literals, stripped)
    stripped = HTML_TAG_PATTERN.sub(" ", stripped)
    stripped = html.unescape(stripped)
    return VISIBLE_TEXT_PATTERN.search(stripped) is not None


def _is_unsafe_translation_unit_source(source_text: str) -> bool:
    """Return true when replacing the unit would drop executable Jinja code."""

    return _contains_jinja_block_or_comment(source_text)


def _contains_jinja_block_or_comment(source_text: str) -> bool:
    return "{%" in source_text


def _contains_raw_jinja_in_translation(translation_text: str) -> bool:
    return RAW_JINJA_IN_TRANSLATION_PATTERN.search(translation_text) is not None


def _is_connector_only_translation_unit(source_text: str) -> bool:
    sentence = _extract_sentence_text(source_text)
    reduced_sentence = re.sub(r"\{[^}]+\}", " ", sentence)
    words = re.findall(r"[A-Za-z]+", reduced_sentence)
    if not words:
        return True
    return all(word.lower() in CONNECTOR_ONLY_WORDS for word in words)


def _hard_fragment_sentence_message(source_text: str) -> str | None:
    sentence = _extract_sentence_text(source_text).strip()
    lowered_sentence = sentence.lower()
    if lowered_sentence in HARD_FRAGMENT_SENTENCES or lowered_sentence.startswith(
        HARD_FRAGMENT_PREFIXES
    ):
        return (
            f"`{sentence}` is only a sentence fragment. Expand/export should keep "
            "the surrounding phrase and any placeholders in the same translation unit."
        )
    return None


def _replace_expr_with_visible_literals(match: re.Match[str]) -> str:
    return " ".join(_extract_translatable_jinja_literals(match.group("expr")))


def _replace_block_with_visible_literals(match: re.Match[str]) -> str:
    token_text = match.group(0)
    if token_text.startswith("{#"):
        return " "
    literals = _extract_translatable_jinja_block_literals(match.group(0)[2:-2])
    if literals:
        return " ".join(literals)
    return " "


def _replace_block_with_sentence_text(match: re.Match[str]) -> str:
    token_text = match.group(0)
    if token_text.startswith("{#"):
        return " "
    inner = token_text[2:-2].strip().strip("-").strip()
    literals = _extract_translatable_jinja_block_literals(inner)
    if literals:
        return " ".join(literals)
    keyword = inner.split(None, 1)[0] if inner else ""
    if keyword in {"elif", "else"}:
        return " / "
    return " "


def _hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _render_translation_document(
    *,
    unit: TranslationUnit,
    source_lang: str,
    target_lang: str,
    translation_text: str,
) -> str:
    return "\n".join(
        [
            "# Translation Unit",
            "",
            f"- Source File: `{unit.source_file}`",
            f"- Wrapper Name: `{unit.wrapper_name}`",
            f"- Wrapper Order: `{unit.wrapper_order}`",
            f"- Wrapper Key: `{unit.wrapper_key}`",
            f"- Unit Key: `{unit.unit_key}`",
            f"- Source Hash: `{unit.unit_source_hash}`",
            f"- Edit only the `Translation ({target_lang})` block below.",
            "",
            f"### Sentence ({source_lang})",
            "",
            "```text",
            _extract_sentence_text(unit.source_text),
            "```",
            "",
            f"### Translation ({target_lang})",
            "",
            SOURCE_FENCE,
            translation_text,
            "~~~",
            "",
        ]
    )


def _parse_translation_document(
    *,
    document_path: Path,
    source_lang: str,
    target_lang: str,
) -> str:
    markdown_text = document_path.read_text(encoding="utf-8")
    sentence_match = SENTENCE_SECTION_PATTERN.search(markdown_text)
    translation_match = TRANSLATION_SECTION_PATTERN.search(markdown_text)
    if sentence_match is None or translation_match is None:
        raise TranslationTreeError(f"Invalid translation document at {document_path}")
    if (
        sentence_match.group("source_lang") != source_lang
        or translation_match.group("target_lang") != target_lang
    ):
        raise TranslationTreeError(
            "Unexpected language headings in translation document at "
            f"{document_path}: expected {source_lang}/{target_lang}"
        )
    return translation_match.group("translation_text")


def _load_existing_translations(
    *,
    output_dir: Path,
    source_lang: str,
    target_lang: str,
) -> dict[tuple[str, str], str]:
    manifest_path = output_dir / TREE_MANIFEST_PATH
    if not manifest_path.is_file():
        return {}
    manifest = _load_tree_manifest(output_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        return {}
    translations: dict[tuple[str, str], str] = {}
    for unit in units:
        source_file = unit.get("source_file")
        unit_key = unit.get("unit_key")
        document_path_raw = unit.get("document_path")
        if (
            not isinstance(source_file, str)
            or not isinstance(unit_key, str)
            or not isinstance(document_path_raw, str)
        ):
            continue
        document_path = output_dir / document_path_raw
        if not document_path.is_file():
            continue
        try:
            translation_text = _parse_translation_document(
                document_path=document_path,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        except TranslationTreeError:
            continue
        translations[(source_file, unit_key)] = translation_text
    return translations


def _load_translations_by_unit_key(
    *,
    tree_dir: Path,
    source_lang: str,
    target_lang: str,
) -> dict[tuple[str, str], TranslationEntry]:
    manifest = _load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )
    translations: dict[tuple[str, str], TranslationEntry] = {}
    for unit in units:
        source_file = unit.get("source_file")
        unit_key = unit.get("unit_key")
        document_path_raw = unit.get("document_path")
        if (
            not isinstance(source_file, str)
            or not isinstance(unit_key, str)
            or not isinstance(document_path_raw, str)
        ):
            raise TranslationTreeError(
                f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
            )
        document_path = tree_dir / document_path_raw
        if not document_path.is_file():
            raise TranslationTreeError(
                f"Missing translation document at {document_path}. "
                "Run `make export-translation-tree` to restore it."
            )
        translation_text = _parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        translations[(source_file, unit_key)] = TranslationEntry(
            text=translation_text,
            document_path=document_path_raw,
        )
    return translations


def _load_tree_manifest(tree_dir: Path) -> dict:
    manifest_path = tree_dir / TREE_MANIFEST_PATH
    if not manifest_path.is_file():
        raise TranslationTreeError(f"Missing translation-tree manifest at {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _build_tree_readme(*, source_lang: str, target_lang: str) -> str:
    return "\n".join(
        [
            "# Translation Tree",
            "",
            "This folder is the translator-facing tree exported from the expanded",
            "template workspace.",
            "",
            f"- Each translation unit has its own `{TRANSLATION_DOC_NAME}` file.",
            f"- Each file starts with a plain `Sentence ({source_lang})` section for",
            "  translator review.",
            "- Wrapper-level blocks from the expanded workspace are split into smaller",
            "  translator-facing units whenever the source structure allows it.",
            f"- Edit only `Translation ({target_lang})` sections.",
            "- Keep every `{placeholder}` shown in the sentence. You may reorder",
            "  placeholders for grammar; sync converts them back to Jinja variables.",
            "- Source hashes in the metadata are machine guards; do not edit them.",
            "- If a translation file is deleted or its markdown block is broken, run",
            "  `make export-translation-tree` to rebuild the file skeleton.",
            "- Run `make sync-translation-tree` to apply translator edits back into a",
            "  generated template copy.",
            "",
        ]
    )


def _render_outline_markdown(*, outline_units: list[OutlineUnit], output_outline: Path) -> str:
    lines = ["### DSW Document Template Translation", ""]
    for source_file in sorted({unit.source_file for unit in outline_units}):
        file_units = [unit for unit in outline_units if unit.source_file == source_file]
        lines.append(
            _render_outline_checkbox_line(
                depth=0,
                is_complete=_all_translated(file_units),
                layer_label="[file]",
                label=f"{source_file} ({_progress_label(file_units)})",
            )
        )
        lines.append("")
        lines.append(f"  [J2] `{source_file}`")
        lines.append("")

        wrapper_orders = sorted({unit.wrapper_order for unit in file_units})
        for wrapper_order in wrapper_orders:
            wrapper_units = [unit for unit in file_units if unit.wrapper_order == wrapper_order]
            wrapper = wrapper_units[0]
            lines.append(
                _render_outline_checkbox_line(
                    depth=1,
                    is_complete=_all_translated(wrapper_units),
                    layer_label="[wrapper]",
                    label=f"{wrapper.wrapper_folder_name} ({_progress_label(wrapper_units)})",
                )
            )
            lines.append("")
            lines.append(f"      [W] `{wrapper.wrapper_folder_name}`")
            lines.append("")

            for unit in wrapper_units:
                relative_link = os.path.relpath(unit.document_path, output_outline.parent)
                formatted_link = _format_link_destination(relative_link)
                lines.append(
                    _render_outline_checkbox_line(
                        depth=2,
                        is_complete=unit.is_translated,
                        layer_label="[unit]",
                        label=f"{unit.unit_folder_name}: {unit.sentence_text}",
                    )
                )
                lines.append("")
                lines.append(f"          [T] [translation]({formatted_link})")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_outline_checkbox_line(
    *,
    depth: int,
    is_complete: bool,
    layer_label: str,
    label: str,
) -> str:
    indent = "    " * depth
    checkbox = "x" if is_complete else " "
    return f"{indent}- [{checkbox}] {layer_label} {label}"


def _all_translated(units: list[OutlineUnit]) -> bool:
    return bool(units) and all(unit.is_translated for unit in units)


def _progress_label(units: list[OutlineUnit]) -> str:
    translated = sum(1 for unit in units if unit.is_translated)
    return f"{translated}/{len(units)}"


def _format_link_destination(destination: str) -> str:
    escaped = destination.replace(">", "\\>")
    return f"<{escaped}>"


def _extract_sentence_text(source_text: str) -> str:
    with_placeholders = JINJA_EXPR_PATTERN.sub(
        lambda match: _jinja_expr_to_placeholder(match.group("expr")),
        source_text,
    )
    without_control = JINJA_COMMENT_OR_BLOCK_PATTERN.sub(
        _replace_block_with_sentence_text,
        with_placeholders,
    )
    with_line_breaks = HTML_BLOCK_END_PATTERN.sub(". ", without_control)
    without_tags = HTML_TAG_PATTERN.sub(" ", with_line_breaks)
    sentence = html.unescape(without_tags)
    sentence = re.sub(r"\s+", " ", sentence).strip()
    sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
    sentence = re.sub(r"([,;:])(?=[^\s/])", r"\1 ", sentence)
    sentence = re.sub(r"\s+/\s*\.", "", sentence)
    sentence = re.sub(r"(?<![/.])\.{2,}", ".", sentence)
    sentence = re.sub(r"(?<![/.])([.!?])\.", r"\1", sentence)
    sentence = re.sub(r"\s+\.", ".", sentence)
    sentence = re.sub(r":\.$", ":", sentence)
    sentence = re.sub(r"^,\s+(available at\b)", r"\1", sentence, flags=re.IGNORECASE)
    sentence = sentence.strip()
    sentence = _repair_sentence_text_glue(sentence)
    return sentence or "(no visible sentence)"


def _repair_sentence_text_glue(sentence: str) -> str:
    repaired = sentence
    for pattern, replacement in SENTENCE_TEXT_REPLACEMENTS:
        repaired = pattern.sub(replacement, repaired)
    return repaired


def _jinja_expr_to_placeholder(expr: str) -> str:
    normalized = " ".join(expr.strip().split())
    literal_value = _literal_expr_to_text(normalized)
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
    indexed_placeholder = _indexed_expr_to_placeholder(base)
    if indexed_placeholder is not None:
        return indexed_placeholder
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", base):
        return "{" + base + "}"
    inferred_placeholder = _identifier_expr_to_placeholder(base)
    if inferred_placeholder is not None:
        return inferred_placeholder
    return "{value}"


def _identifier_expr_to_placeholder(expr: str) -> str | None:
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


def _indexed_expr_to_placeholder(expr: str) -> str | None:
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


def _literal_expr_to_text(expr: str) -> str | None:
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


def _validate_expanded_workspace(source_dir: Path) -> None:
    manifest_path = source_dir / MANIFEST_PATH
    if not manifest_path.is_file():
        raise TranslationTreeError(
            f"Expanded workspace is missing transform manifest at {manifest_path}"
        )


def _wrap_translatable_block(block_name: str, source_text: str) -> str:
    return f"{{# {block_name}:start #}}{source_text}{{# {block_name}:end #}}"


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
