"""Translator-facing tree export and sync for expanded DSW templates."""

from __future__ import annotations

import ast
import hashlib
import html
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .template_transform import (
    ANNOTATABLE_HTML_TAGS,
    GENERATED_BLOCK_PATTERN,
    MANIFEST_PATH,
    AnnotationRegion,
    SourceToken,
    _extract_translatable_jinja_block_literals,
    _extract_translatable_jinja_literals,
    _find_matching_tag_end,
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
TEXT_SECTION_PATTERN = re.compile(
    r"### Source \((?P<source_lang>[^)]+)\)\n\n~~~jinja\n"
    r"(?P<source_text>.*?)\n~~~\n\n"
    r"### Translation \((?P<target_lang>[^)]+)\)\n\n~~~jinja\n"
    r"(?P<translation_text>.*?)\n~~~\n?\Z",
    re.DOTALL,
)
JINJA_COMMENT_OR_BLOCK_PATTERN = re.compile(r"\{#.*?#\}|\{%.*?%\}", re.DOTALL)
JINJA_EXPR_PATTERN = re.compile(r"\{\{\s*(?P<expr>.*?)\s*\}\}", re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
HTML_BLOCK_END_PATTERN = re.compile(
    r"</(?:p|li|h[1-6]|dt|dd|th|td|caption)>|<br\s*/?>",
    re.IGNORECASE,
)
VISIBLE_TEXT_PATTERN = re.compile(r"[A-Za-z0-9]+")
TRANSLATION_TREE_HTML_TAGS = ANNOTATABLE_HTML_TAGS | {
    "a",
    "em",
    "small",
    "span",
    "strong",
}


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

    _reset_dir(output_dir)
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)

    units_by_file: dict[str, list[dict[str, str | int]]] = {}
    for unit in units:
        source_file = unit["source_file"]
        if not isinstance(source_file, str):
            raise TranslationTreeError(
                f"Invalid source_file in translation-tree manifest: {source_file!r}"
            )
        units_by_file.setdefault(source_file, []).append(unit)

    for source_file, file_units in units_by_file.items():
        destination_path = output_dir / source_file
        destination_text = destination_path.read_text(encoding="utf-8")
        wrapper_matches = list(GENERATED_BLOCK_PATTERN.finditer(destination_text))

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
            rebuilt_parts.append(destination_text[cursor : match.start()])

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

        rebuilt_parts.append(destination_text[cursor:])
        destination_path.write_text("".join(rebuilt_parts), encoding="utf-8")

    return output_dir


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

        for unit_index, region in enumerate(unit_regions, start=1):
            unit_text = wrapper_body[region.start : region.end]
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
        inner_regions = _collect_translation_unit_regions(inner_text)
        normalized_inner_regions = _normalize_regions(
            regions=inner_regions,
            source_text=wrapper_body,
            base_offset=inner_start,
        )
        if normalized_inner_regions:
            return normalized_inner_regions

    normalized_regions = _normalize_regions(
        regions=_collect_translation_unit_regions(wrapper_body),
        source_text=wrapper_body,
        base_offset=0,
    )
    if normalized_regions:
        return normalized_regions

    return [AnnotationRegion(start=0, end=len(wrapper_body))]


def _collect_translation_unit_regions(source_text: str) -> list[AnnotationRegion]:
    tokens = _lex_source_tokens(source_text)
    element_regions = _collect_leaf_element_regions(tokens=tokens, source_text=source_text)
    inline_regions = _collect_inline_text_regions(
        tokens=tokens,
        source_text=source_text,
        covered_regions=element_regions,
    )
    return sorted(element_regions + inline_regions, key=lambda item: item.start)


def _collect_leaf_element_regions(
    *, tokens: list[SourceToken], source_text: str
) -> list[AnnotationRegion]:
    candidate_regions: list[AnnotationRegion] = []
    for index, token in enumerate(tokens):
        if (
            token.kind == "html_tag"
            and token.is_opening_tag
            and not token.is_self_closing_tag
            and token.tag_name in TRANSLATION_TREE_HTML_TAGS
        ):
            end_index = _find_matching_tag_end(tokens=tokens, start_index=index)
            if end_index is None:
                continue
            region = AnnotationRegion(start=token.start, end=tokens[end_index].end)
            if _contains_translatable_text(source_text[region.start : region.end]):
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
        # Control blocks often split one rendered sentence; keep them in the same
        # inline region so translators do not see bare connectors such as "and".
        if token.kind in {"text", "jinja_expr", "jinja_block", "jinja_comment"}:
            pending_tokens.append(token)
            continue
        flush_pending()

    flush_pending()
    return regions


def _is_inside_region(*, token: SourceToken, regions: list[AnnotationRegion]) -> bool:
    return any(region.start <= token.start and token.end <= region.end for region in regions)


def _find_single_outer_element_inner_bounds(*, tokens: list[SourceToken]) -> tuple[int, int] | None:
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

    if any(not _is_ignorable_outer_token(token) for token in tokens[:first_index]):
        return None
    if any(not _is_ignorable_outer_token(token) for token in tokens[end_index + 1 :]):
        return None

    return (first_token.end, tokens[end_index].start)


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
        start = base_offset + region.start
        end = base_offset + region.end
        while start < end and source_text[start].isspace():
            start += 1
        while end > start and source_text[end - 1].isspace():
            end -= 1
        if start >= end:
            continue
        if not _contains_translatable_text(source_text[start:end]):
            continue
        if normalized and start < normalized[-1].end:
            continue
        normalized.append(AnnotationRegion(start=start, end=end))
    return normalized


def _apply_unit_translations(
    *,
    source_file: str,
    wrapper_body: str,
    wrapper_units: list[dict[str, str | int]],
    translations: dict[tuple[str, str], str],
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
        translation_text = translations.get((source_file, unit_key)) or source_unit_text
        rebuilt_parts.append(translation_text)
        cursor = unit_end

    rebuilt_parts.append(wrapper_body[cursor:])
    return "".join(rebuilt_parts)


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
            f"### Source ({source_lang})",
            "",
            SOURCE_FENCE,
            unit.source_text,
            "~~~",
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
) -> tuple[str, str]:
    markdown_text = document_path.read_text(encoding="utf-8")
    match = TEXT_SECTION_PATTERN.search(markdown_text)
    if match is None:
        raise TranslationTreeError(f"Invalid translation document at {document_path}")
    if match.group("source_lang") != source_lang or match.group("target_lang") != target_lang:
        raise TranslationTreeError(
            "Unexpected language headings in translation document at "
            f"{document_path}: expected {source_lang}/{target_lang}"
        )
    return match.group("source_text"), match.group("translation_text")


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
        _, translation_text = _parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        translations[(source_file, unit_key)] = translation_text
    return translations


def _load_translations_by_unit_key(
    *,
    tree_dir: Path,
    source_lang: str,
    target_lang: str,
) -> dict[tuple[str, str], str]:
    manifest = _load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )
    translations: dict[tuple[str, str], str] = {}
    for unit in units:
        source_file = unit.get("source_file")
        unit_key = unit.get("unit_key")
        unit_source_hash = unit.get("unit_source_hash")
        document_path_raw = unit.get("document_path")
        if (
            not isinstance(source_file, str)
            or not isinstance(unit_key, str)
            or not isinstance(unit_source_hash, str)
            or not isinstance(document_path_raw, str)
        ):
            raise TranslationTreeError(
                f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
            )
        document_path = tree_dir / document_path_raw
        source_text, translation_text = _parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        if _hash_text(source_text) != unit_source_hash:
            raise TranslationTreeError(
                "Source section changed in translation document at "
                f"{document_path}. Re-run `make export-translation-tree`."
            )
        translations[(source_file, unit_key)] = translation_text
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
            "  translator review, followed by the original Jinja source.",
            "- Wrapper-level blocks from the expanded workspace are split into smaller",
            "  translator-facing units whenever the source structure allows it.",
            f"- Edit only `Translation ({target_lang})` sections.",
            f"- `Source ({source_lang})` sections are the machine-exported source of truth.",
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
    sentence = re.sub(r"([,;:])(?=\S)", r"\1 ", sentence)
    sentence = re.sub(r"\.{2,}", ".", sentence)
    sentence = re.sub(r"([.!?])\.", r"\1", sentence)
    sentence = re.sub(r"\s+\.", ".", sentence)
    sentence = sentence.strip()
    return sentence or "(no visible sentence)"


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
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", base):
        return "{" + base + "}"
    return "{value}"


def _literal_expr_to_text(expr: str) -> str | None:
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
