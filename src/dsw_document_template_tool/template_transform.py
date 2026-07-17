"""Reversible expansion helpers for translation-friendly DSW templates."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ._template_transform.append_sentences import (
    restore_append_sentence_rewrites as _restore_append_sentence_rewrites,
)
from ._template_transform.append_sentences import (
    rewrite_append_sentence_literals as _rewrite_append_sentence_literals,
)
from ._template_transform.branch_sentences import (
    restore_branch_sentence_rewrites as _restore_branch_sentence_rewrites,
)
from ._template_transform.branch_sentences import (
    rewrite_common_prefix_branch_sentences as _rewrite_common_prefix_branch_sentences,
)
from ._template_transform.inline_conditionals import (
    restore_inline_conditional_rewrites as _restore_inline_conditional_rewrites,
)
from ._template_transform.inline_conditionals import (
    rewrite_inline_conditional_expressions as _rewrite_inline_conditional_expressions,
)
from ._template_transform.jinja_literals import (
    rendered_joined_collection_names as _rendered_collections,
)
from ._template_transform.jinja_literals import (
    translatable_rendered_list_initializer_literals as _rendered_list_literals,
)
from ._template_transform.localization import (
    LocalizationPatchError,
)
from ._template_transform.localization import (
    apply_post_expand_patches as _apply_post_expand_patches,
)
from ._template_transform.localization import (
    build_post_expand_patch_state as _build_post_expand_patch_state,
)
from ._template_transform.localization import (
    revert_post_expand_patches as _revert_post_expand_patches,
)
from ._template_transform.markers import (
    GENERATED_BLOCK_PATTERN,
    GENERATED_BLOCK_PREFIX,
    generated_block_body,
)
from ._template_transform.models import TemplateTransformError
from ._template_transform.profile import (
    TransformContext,
    TransformTrace,
    read_template_identity,
)
from ._template_transform.scanner import (
    ANNOTATABLE_HTML_TAGS,
    AnnotationRegion,
    SourceToken,
)
from ._template_transform.scanner import (
    find_matching_tag_end as _find_matching_tag_end,
)
from ._template_transform.scanner import (
    lex_source_tokens as _lex_source_tokens,
)
from ._template_transform.science_europe import (
    PROFILE_ID as SCIENCE_EUROPE_PROFILE_ID,
)
from ._template_transform.science_europe import (
    is_science_europe_template,
    rewrite_science_europe_source,
)
from ._template_transform.text_visibility import (
    contains_translatable_text as _contains_translatable_text,
)
from ._template_transform.text_visibility import (
    is_translatable_jinja_block as _is_translatable_jinja_block,
)
from ._template_transform.workspace import (
    MANIFEST_PATH,
    UPSTREAM_README_NAME,
)
from ._template_transform.workspace import (
    reset_dir as _reset_dir,
)
from ._template_transform.workspace import (
    rewrite_workspace_readme as _rewrite_workspace_readme,
)
from ._template_transform.workspace import (
    snapshot_tree as snapshot_tree,
)
from ._template_transform.workspace import (
    validate_template_dir as _validate_template_dir,
)

MANIFEST_VERSION = 2
README_NAME = "README.md"


def expand_template_dir(
    *,
    source_dir: Path,
    output_dir: Path,
    apply_local_patches: bool = True,
) -> Path:
    """Expand one compact DSW template directory into a translation workspace."""

    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    _validate_template_dir(source_dir)
    identity = read_template_identity(source_dir)
    profile_id = SCIENCE_EUROPE_PROFILE_ID if is_science_europe_template(identity) else "generic"
    trace = TransformTrace(profile_id=profile_id)
    _reset_dir(output_dir)
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)

    transformed_files: list[str] = []
    for source_path in sorted(source_dir.rglob("*.j2")):
        relative_path = source_path.relative_to(source_dir)
        expanded_text = _expand_template_text(
            source_text=source_path.read_text(encoding="utf-8"),
            context=TransformContext(
                identity=identity,
                relative_path=relative_path.as_posix(),
                apply_local_patches=apply_local_patches,
            ),
            trace=trace,
        )
        destination_path = output_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(expanded_text, encoding="utf-8")
        transformed_files.append(relative_path.as_posix())

    _rewrite_workspace_readme(source_dir=source_dir, output_dir=output_dir)
    post_expand_patch_state: dict[str, object] = {}
    post_expand_patches: list[str] = []
    if apply_local_patches and is_science_europe_template(identity):
        post_expand_patch_state = _build_post_expand_patch_state(output_dir=output_dir)
        try:
            post_expand_patches = _apply_post_expand_patches(output_dir=output_dir)
        except LocalizationPatchError as exc:
            raise TemplateTransformError(str(exc)) from exc

    manifest = {
        "version": MANIFEST_VERSION,
        "format": "sentence_comment_markers",
        "files": transformed_files,
        "workspace_readme": README_NAME,
        "upstream_readme": UPSTREAM_README_NAME if (source_dir / README_NAME).is_file() else None,
        "post_expand_patches": post_expand_patches,
        "post_expand_patch_state": post_expand_patch_state,
        "template_id": identity.full_id,
        "rewrite_trace": trace.to_manifest(),
    }
    manifest_path = output_dir / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_dir


def compact_template_dir(*, source_dir: Path, output_dir: Path) -> Path:
    """Compact one expanded translation workspace back into DSW uploadable form."""

    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    manifest_path = source_dir / MANIFEST_PATH
    if not manifest_path.is_file():
        raise TemplateTransformError(
            f"Expanded template is missing transform manifest at {manifest_path}"
        )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    transformed_files = payload.get("files")
    if not isinstance(transformed_files, list):
        raise TemplateTransformError(f"Invalid transform manifest at {manifest_path}")

    _reset_dir(output_dir)
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)

    for relative_raw in transformed_files:
        if not isinstance(relative_raw, str) or not relative_raw:
            raise TemplateTransformError(
                f"Transform manifest file entry must be a non-empty string: {relative_raw!r}"
            )
        relative_path = Path(relative_raw)
        source_path = output_dir / relative_path
        compacted_text = _restore_append_sentence_rewrites(source_path.read_text(encoding="utf-8"))
        compacted_text = _restore_branch_sentence_rewrites(compacted_text)
        compacted_text = GENERATED_BLOCK_PATTERN.sub(
            lambda match: generated_block_body(match),
            compacted_text,
        )
        compacted_text = _restore_inline_conditional_rewrites(compacted_text)
        source_path.write_text(compacted_text, encoding="utf-8")

    shutil.rmtree(output_dir / MANIFEST_PATH.parent, ignore_errors=True)
    upstream_readme = payload.get("upstream_readme")
    if isinstance(upstream_readme, str) and upstream_readme:
        upstream_path = output_dir / upstream_readme
        if upstream_path.is_file():
            (output_dir / README_NAME).write_text(
                upstream_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            upstream_path.unlink()
    else:
        workspace_readme = payload.get("workspace_readme")
        if isinstance(workspace_readme, str) and workspace_readme:
            (output_dir / workspace_readme).unlink(missing_ok=True)
    _revert_post_expand_patches(
        output_dir=output_dir,
        patches=payload.get("post_expand_patches"),
        patch_state=payload.get("post_expand_patch_state"),
    )
    return output_dir


def explain_transform_workspace(source_dir: Path) -> str:
    """Render a concise rule trace from an expanded workspace manifest."""

    manifest_path = Path(source_dir).resolve() / MANIFEST_PATH
    if not manifest_path.is_file():
        raise TemplateTransformError(
            f"Expanded template is missing transform manifest at {manifest_path}"
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateTransformError(
            f"Invalid transform manifest at {manifest_path}: {exc}"
        ) from exc
    trace = payload.get("rewrite_trace")
    if not isinstance(trace, dict):
        raise TemplateTransformError(f"Transform manifest at {manifest_path} has no rewrite trace")
    profile = trace.get("profile")
    applications = trace.get("applications")
    if not isinstance(profile, str) or not isinstance(applications, list):
        raise TemplateTransformError(f"Invalid rewrite trace in {manifest_path}")

    lines = [
        f"Template: {payload.get('template_id', '(unknown)')}",
        f"Profile: {profile}",
        f"Applied rule locations: {len(applications)}",
    ]
    for item in applications:
        if not isinstance(item, dict):
            raise TemplateTransformError(f"Invalid rewrite trace application in {manifest_path}")
        lines.append(
            f"- {item.get('group_id', '(unknown)')} "
            f"[{item.get('source_file', '(unknown)')}] x{item.get('match_count', 0)}\n"
            f"  {item.get('rationale', '(no rationale)')}"
        )
    return "\n".join(lines)


def _expand_template_text(
    *,
    source_text: str,
    context: TransformContext,
    trace: TransformTrace,
) -> str:
    source_text = _rewrite_append_sentence_literals(source_text)
    if is_science_europe_template(context.identity):
        source_text = rewrite_science_europe_source(
            source_text,
            context=context,
            trace=trace,
            phase="balanced",
        )
    source_text = _rewrite_inline_conditional_expressions(source_text)
    source_text = _rewrite_common_prefix_branch_sentences(source_text)
    if is_science_europe_template(context.identity):
        source_text = rewrite_science_europe_source(
            source_text,
            context=context,
            trace=trace,
            phase="unbalanced",
        )
    tokens = _lex_source_tokens(source_text)
    regions = _collect_annotation_regions(tokens=tokens, source_text=source_text)

    expanded_parts: list[str] = []
    cursor = 0
    for segment_index, region in enumerate(regions):
        expanded_parts.append(source_text[cursor : region.start])
        block_name = f"{GENERATED_BLOCK_PREFIX}{segment_index:04d}"
        expanded_parts.append(
            _wrap_translatable_block(block_name, source_text[region.start : region.end])
        )
        cursor = region.end
    expanded_parts.append(source_text[cursor:])
    return "".join(expanded_parts)


def _wrap_translatable_block(block_name: str, source_text: str) -> str:
    return f"{{# {block_name}:start #}}{source_text}{{# {block_name}:end #}}"


def _collect_annotation_regions(
    *, tokens: list[SourceToken], source_text: str
) -> list[AnnotationRegion]:
    element_regions = _collect_element_regions(tokens=tokens, source_text=source_text)
    initializer_regions = _collect_rendered_list_initializer_regions(
        tokens=tokens,
        source_text=source_text,
        covered_regions=element_regions,
    )
    inline_regions = _collect_inline_text_regions(
        tokens=tokens,
        source_text=source_text,
        covered_regions=element_regions + initializer_regions,
    )
    return sorted(
        element_regions + initializer_regions + inline_regions,
        key=lambda item: item.start,
    )


def _collect_rendered_list_initializer_regions(
    *,
    tokens: list[SourceToken],
    source_text: str,
    covered_regions: list[AnnotationRegion],
) -> list[AnnotationRegion]:
    """Find static list seeds whose collection is later rendered with ``join``."""

    rendered_names = _rendered_collections(source_text)
    if not rendered_names:
        return []

    regions: list[AnnotationRegion] = []
    for token in tokens:
        if token.kind != "jinja_block" or _is_inside_covered_region(
            token=token,
            covered_regions=covered_regions,
        ):
            continue
        if _rendered_list_literals(
            token_text=token.text,
            rendered_collection_names=rendered_names,
        ):
            regions.append(AnnotationRegion(start=token.start, end=token.end))
    return regions


def _collect_element_regions(
    *, tokens: list[SourceToken], source_text: str
) -> list[AnnotationRegion]:
    regions: list[AnnotationRegion] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if (
            token.kind == "html_tag"
            and token.is_opening_tag
            and not token.is_self_closing_tag
            and token.tag_name in ANNOTATABLE_HTML_TAGS
        ):
            end_index = _find_matching_tag_end(tokens=tokens, start_index=index)
            if end_index is not None:
                region = AnnotationRegion(start=token.start, end=tokens[end_index].end)
                if _contains_translatable_text(source_text[region.start : region.end]):
                    regions.append(region)
                index = end_index + 1
                continue
        index += 1
    return regions


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
        if _is_inside_covered_region(token=token, covered_regions=covered_regions):
            flush_pending()
            continue
        if token.kind in {"text", "jinja_expr"} or (
            token.kind == "jinja_block" and _is_translatable_jinja_block(token.text)
        ):
            pending_tokens.append(token)
            continue
        flush_pending()

    flush_pending()
    return regions


def _is_inside_covered_region(
    *, token: SourceToken, covered_regions: list[AnnotationRegion]
) -> bool:
    return any(
        region.start <= token.start and token.end <= region.end for region in covered_regions
    )
