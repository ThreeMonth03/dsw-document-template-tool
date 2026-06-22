"""Translator-facing tree export and sync for expanded DSW templates."""

from __future__ import annotations

import ast
import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from ._translation_tree.apply import apply_unit_translations
from ._translation_tree.document import (
    TRANSLATION_DOC_NAME,
    render_translation_document,
    render_tree_readme,
)
from ._translation_tree.filesystem import reset_dir
from ._translation_tree.html_structure import (
    INLINE_TRANSLATOR_TAGS,
    find_single_outer_element_inner_bounds,
)
from ._translation_tree.ids import hash_text
from ._translation_tree.manifest import (
    TREE_MANIFEST_PATH,
    TREE_VERSION,
    load_tree_manifest,
)
from ._translation_tree.metadata import patch_template_metadata
from ._translation_tree.models import (
    OutlineUnit,
    TranslationTreeError,
    TranslationUnit,
)
from ._translation_tree.outline import render_outline_markdown
from ._translation_tree.placeholders import literal_expr_to_text
from ._translation_tree.source_text import (
    build_folder_name as _build_folder_name,
)
from ._translation_tree.source_text import (
    build_unit_key as _build_unit_key,
)
from ._translation_tree.source_text import (
    build_wrapper_key as _build_wrapper_key,
)
from ._translation_tree.source_text import (
    contains_jinja_block_or_comment as _contains_jinja_block_or_comment,
)
from ._translation_tree.source_text import (
    contains_translatable_text as _contains_translatable_text,
)
from ._translation_tree.source_text import (
    extract_sentence_text as _extract_sentence_text,
)
from ._translation_tree.source_text import (
    is_connector_only_translation_unit as _is_connector_only_translation_unit,
)
from ._translation_tree.source_text import (
    is_unsafe_translation_unit_source as _is_unsafe_translation_unit_source,
)
from ._translation_tree.store import (
    load_existing_translations,
    load_translations_by_unit_key,
)
from ._translation_tree.structure_audit import (
    audit_translated_template_structure as audit_translated_template_structure,
)
from ._translation_tree.syntax import (
    HTML_TAG_PATTERN,
    JINJA_COMMENT_OR_BLOCK_PATTERN,
    JINJA_EXPR_PATTERN,
)
from ._translation_tree.tree_audit import audit_translation_tree as audit_translation_tree
from ._translation_tree.workspace import validate_expanded_workspace
from .template_transform import (
    ANNOTATABLE_HTML_TAGS,
    GENERATED_BLOCK_PATTERN,
    JINJA_STRING_LITERAL_PATTERN,
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

TREE_ROOT_NAME = "tree"
DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "zh_Hant"
HTML_CONTEXT_BOUNDARY_PATTERN = re.compile(
    r"</(?:p|li|h[1-6]|dt|dd|th|td|caption|div|ul|ol|table|tr)>|<br\s*/?>",
    re.IGNORECASE,
)


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
    validate_expanded_workspace(source_dir)
    existing_translations = load_existing_translations(
        output_dir=output_dir,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    reset_dir(output_dir)
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
                render_translation_document(
                    unit=unit,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    sentence_text=_extract_sentence_text(unit.source_text),
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
        render_tree_readme(
            source_lang=source_lang,
            target_lang=target_lang,
        ),
        encoding="utf-8",
    )
    (output_dir / "outline.md").write_text(
        render_outline_markdown(
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
    validate_expanded_workspace(source_dir)
    manifest = load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )

    translations = load_translations_by_unit_key(
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
            wrapper_hash = hash_text(wrapper_body)
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
                    apply_unit_translations(
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

    reset_dir(output_dir)
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)
    for source_file, translated_text in translated_files.items():
        (output_dir / source_file).write_text(translated_text, encoding="utf-8")
    patch_template_metadata(
        output_dir=output_dir,
        organization_id=template_organization_id,
        template_id=template_id,
        name=template_name,
        version=template_version,
    )

    return output_dir


def _extract_units(*, relative_path: str, source_text: str) -> list[TranslationUnit]:
    units: list[TranslationUnit] = []
    key_counts: dict[str, int] = {}

    for wrapper_index, match in enumerate(GENERATED_BLOCK_PATTERN.finditer(source_text), start=1):
        wrapper_name = generated_block_name(match)
        wrapper_body = generated_block_body(match)
        wrapper_key = _build_wrapper_key(relative_path=relative_path, source_text=wrapper_body)
        wrapper_folder_name = _build_folder_name(index=wrapper_index, slug=wrapper_key)
        wrapper_source_hash = hash_text(wrapper_body)
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
                    unit_source_hash=hash_text(unit_text),
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
    outer_bounds = find_single_outer_element_inner_bounds(tokens=tokens)
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
    if literal_expr_to_text(expr) is not None:
        return True
    return not _extract_translatable_jinja_literals(expr)


def _is_inside_region(*, token: SourceToken, regions: list[AnnotationRegion]) -> bool:
    return any(region.start <= token.start and token.end <= region.end for region in regions)


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


def _wrap_translatable_block(block_name: str, source_text: str) -> str:
    return f"{{# {block_name}:start #}}{source_text}{{# {block_name}:end #}}"
