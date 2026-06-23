"""Reversible expansion helpers for translation-friendly DSW templates."""

from __future__ import annotations

import ast
import base64
import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from ._template_transform.jinja_literals import (
    extract_translatable_jinja_block_literals as _extract_translatable_jinja_block_literals,
)
from ._template_transform.jinja_literals import (
    extract_translatable_jinja_literals as _extract_translatable_jinja_literals,
)
from ._template_transform.jinja_literals import (
    is_translatable_jinja_literal as _is_translatable_jinja_literal,
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
from ._template_transform.scanner import (
    ANNOTATABLE_HTML_TAGS,
    HTML_TAG_PATTERN,
    JINJA_BLOCK_PATTERN,
    JINJA_EXPR_PATTERN,
    VISIBLE_TEXT_PATTERN,
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
    rewrite_science_europe_balanced_source_fragments,
    rewrite_science_europe_unbalanced_html_fragments,
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

INLINE_CONDITIONAL_REWRITE_PATTERN = re.compile(
    r"\{# __tr_inline_if_original:(?P<payload>[A-Za-z0-9_-]+=*) #\}"
    r".*?"
    r"\{# __tr_inline_if_original:end #\}",
    re.DOTALL,
)
BRANCH_SENTENCE_REWRITE_PATTERN = re.compile(
    r"\{# __tr_branch_sentence_original:(?P<payload>[A-Za-z0-9_-]+=*) #\}"
    r".*?"
    r"\{# __tr_branch_sentence_original:end #\}",
    re.DOTALL,
)
APPEND_SENTENCE_REWRITE_PATTERN = re.compile(
    r"\{# __tr_append_sentence_original:(?P<payload>[A-Za-z0-9_-]+=*) #\}"
    r".*?"
    r"\{# __tr_append_sentence_original:end -?#\}",
    re.DOTALL,
)
MANIFEST_VERSION = 2


@dataclass(frozen=True)
class BranchRewriteBranch:
    """One if/elif/else branch body inside a rewriteable Jinja group."""

    opener_text: str
    start: int
    end: int
    rstrip_body: bool


@dataclass(frozen=True)
class BranchRewriteGroup:
    """One rewriteable top-level Jinja if group."""

    start: int
    end: int
    end_text: str
    branches: tuple[BranchRewriteBranch, ...]


def expand_template_dir(*, source_dir: Path, output_dir: Path) -> Path:
    """Expand one compact DSW template directory into a translation workspace."""

    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    _validate_template_dir(source_dir)
    _reset_dir(output_dir)
    shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)

    transformed_files: list[str] = []
    for source_path in sorted(source_dir.rglob("*.j2")):
        relative_path = source_path.relative_to(source_dir)
        expanded_text = _expand_template_text(
            source_text=source_path.read_text(encoding="utf-8"),
        )
        destination_path = output_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(expanded_text, encoding="utf-8")
        transformed_files.append(relative_path.as_posix())

    _rewrite_workspace_readme(source_dir=source_dir, output_dir=output_dir)
    post_expand_patch_state = _build_post_expand_patch_state(output_dir=output_dir)
    try:
        post_expand_patches = _apply_post_expand_patches(output_dir=output_dir)
    except LocalizationPatchError as exc:
        raise TemplateTransformError(str(exc)) from exc

    manifest = {
        "version": MANIFEST_VERSION,
        "format": "sentence_comment_markers",
        "files": transformed_files,
        "workspace_readme": "README.md",
        "upstream_readme": UPSTREAM_README_NAME if (source_dir / "README.md").is_file() else None,
        "post_expand_patches": post_expand_patches,
        "post_expand_patch_state": post_expand_patch_state,
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
            (output_dir / "README.md").write_text(
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


def _expand_template_text(*, source_text: str) -> str:
    source_text = _rewrite_append_sentence_literals(source_text)
    source_text = rewrite_science_europe_balanced_source_fragments(source_text)
    source_text = _rewrite_inline_conditional_expressions(source_text)
    source_text = _rewrite_common_prefix_branch_sentences(source_text)
    source_text = rewrite_science_europe_unbalanced_html_fragments(source_text)
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


def _rewrite_append_sentence_literals(source_text: str) -> str:
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

        inner = _jinja_block_inner(original)
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
        encoded_original = base64.urlsafe_b64encode(original.encode("utf-8")).decode("ascii")
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


def _append_sentence_rewrite_statement(
    append_match: re.Match[str],
    target: str,
    variable_name: str,
) -> str:
    if append_match.group("mode") == "do":
        return f"{{%- do {target}.append({variable_name}) -%}}"
    set_name = append_match.group("set_name") or "_"
    return f"{{%- set {set_name} = {target}.append({variable_name}) -%}}"


def _restore_append_sentence_rewrites(source_text: str) -> str:
    """Restore original append statements when compacting a workspace."""

    def replace(match: re.Match[str]) -> str:
        try:
            return base64.urlsafe_b64decode(match.group("payload")).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise TemplateTransformError("Invalid append sentence rewrite marker") from exc

    return APPEND_SENTENCE_REWRITE_PATTERN.sub(replace, source_text)


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
            if _is_translatable_jinja_literal(literal):
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


def _wrap_translatable_block(block_name: str, source_text: str) -> str:
    return f"{{# {block_name}:start #}}{source_text}{{# {block_name}:end #}}"


def _rewrite_inline_conditional_expressions(source_text: str) -> str:
    """Expand inline Jinja ternaries so fallback strings can be translated safely."""

    def replace(match: re.Match[str]) -> str:
        original = match.group(0)
        parts = _split_inline_conditional_expression(match.group("expr"))
        if parts is None:
            return original
        true_expr, condition_expr, false_expr = parts
        if not _should_rewrite_inline_conditional(true_expr=true_expr, false_expr=false_expr):
            return original
        encoded_original = base64.urlsafe_b64encode(original.encode("utf-8")).decode("ascii")
        return (
            f"{{# __tr_inline_if_original:{encoded_original} #}}"
            f"{{% if {condition_expr} %}}{{{{ {true_expr} }}}}"
            f"{{% else %}}{{{{ {false_expr} }}}}{{% endif %}}"
            "{# __tr_inline_if_original:end #}"
        )

    return JINJA_EXPR_PATTERN.sub(replace, source_text)


def _restore_inline_conditional_rewrites(source_text: str) -> str:
    """Restore original inline ternaries when compacting an expanded workspace."""

    def replace(match: re.Match[str]) -> str:
        try:
            return base64.urlsafe_b64decode(match.group("payload")).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise TemplateTransformError("Invalid inline conditional rewrite marker") from exc

    return INLINE_CONDITIONAL_REWRITE_PATTERN.sub(replace, source_text)


def _rewrite_common_prefix_branch_sentences(source_text: str) -> str:
    """Duplicate shared sentence parts into simple mutually exclusive branches."""

    tokens = _lex_source_tokens(source_text)
    rewrite_regions: list[tuple[int, int, str]] = []

    for start_index, token in enumerate(tokens):
        if (
            token.kind != "html_tag"
            or not token.is_opening_tag
            or token.is_self_closing_tag
            or token.tag_name not in ANNOTATABLE_HTML_TAGS
        ):
            continue
        end_index = _find_matching_tag_end(tokens=tokens, start_index=start_index)
        if end_index is None:
            continue
        end_token = tokens[end_index]
        if (
            end_token.kind != "html_tag"
            or not end_token.is_closing_tag
            or end_token.tag_name != token.tag_name
        ):
            continue

        inner_start = token.end
        inner_end = end_token.start
        inner_text = source_text[inner_start:inner_end]
        active_conditions = _active_jinja_if_conditions_at(tokens=tokens, token_index=start_index)
        rewritten_inner = _rewrite_inner_common_prefix_branch(
            inner_text,
            opening_tag=token.text,
            closing_tag=end_token.text,
            active_conditions=active_conditions,
        )
        if rewritten_inner is None:
            continue

        original_region = source_text[token.start : end_token.end]
        encoded_original = base64.urlsafe_b64encode(original_region.encode("utf-8")).decode("ascii")
        rewritten_region = (
            f"{{# __tr_branch_sentence_original:{encoded_original} #}}"
            f"{rewritten_inner}"
            "{# __tr_branch_sentence_original:end #}"
        )
        rewrite_regions.append((token.start, end_token.end, rewritten_region))

    if not rewrite_regions:
        return source_text
    return _replace_non_overlapping_regions(source_text, rewrite_regions)


def _rewrite_inner_common_prefix_branch(
    inner_text: str,
    *,
    opening_tag: str,
    closing_tag: str,
    active_conditions: list[str],
) -> str | None:
    inner_tokens = _lex_source_tokens(inner_text)
    groups = _collect_top_level_branch_rewrite_groups(tokens=inner_tokens)
    if len(groups) == 1:
        rewritten_group = _rewrite_single_alternative_branch_group(
            inner_text=inner_text,
            opening_tag=opening_tag,
            closing_tag=closing_tag,
            group=groups[0],
            active_conditions=active_conditions,
        )
        if rewritten_group is not None:
            return rewritten_group

    optional_groups = _collect_top_level_optional_rewrite_groups(tokens=inner_tokens)
    if len(optional_groups) == 1:
        rewritten_group = _rewrite_single_alternative_branch_group(
            inner_text=inner_text,
            opening_tag=opening_tag,
            closing_tag=closing_tag,
            group=optional_groups[0],
            active_conditions=active_conditions,
        )
        if rewritten_group is not None:
            return rewritten_group

    rewritten_single_choice = _rewrite_single_choice_optional_branch_groups(
        inner_text=inner_text,
        opening_tag=opening_tag,
        closing_tag=closing_tag,
        active_conditions=active_conditions,
    )
    if rewritten_single_choice is not None:
        return rewritten_single_choice

    rewritten_nested_fragments = _rewrite_nested_common_prefix_branch_fragments(inner_text)
    if rewritten_nested_fragments is not None:
        return f"{opening_tag}{rewritten_nested_fragments}{closing_tag}"

    return None


def _rewrite_nested_common_prefix_branch_fragments(inner_text: str) -> str | None:
    """Rewrite nested branch fragments inside a larger sentence-preserving element.

    Some templates have a paragraph-level optional fragment followed by a nested
    if/elif reason, for example `available with {% if reason %}...`.  The outer
    paragraph cannot be fully expanded without a Cartesian explosion, but the
    nested branch can still duplicate its immediate visible prefix so translators
    do not receive `available with` or `because ...` as disconnected units.
    """

    rewritten = _rewrite_common_prefix_branch_fragments(inner_text)
    if rewritten == inner_text:
        return None
    return rewritten


def _rewrite_common_prefix_branch_fragments(source_text: str) -> str:
    tokens = _lex_source_tokens(source_text)
    groups = _collect_top_level_branch_rewrite_groups(tokens=tokens)
    if len(groups) == 1:
        rewritten = _rewrite_single_alternative_branch_fragment(
            source_text=source_text,
            group=groups[0],
        )
        if rewritten is not None:
            return rewritten

    replacements: list[tuple[int, int, str]] = []
    for group in _collect_top_level_optional_rewrite_groups(tokens=tokens):
        for branch in group.branches:
            branch_text = source_text[branch.start : branch.end]
            rewritten_branch = _rewrite_common_prefix_branch_fragments(branch_text)
            if rewritten_branch != branch_text:
                replacements.append((branch.start, branch.end, rewritten_branch))

    if not replacements:
        return source_text
    return _replace_non_overlapping_regions(source_text, replacements)


def _rewrite_single_alternative_branch_fragment(
    *,
    source_text: str,
    group: BranchRewriteGroup,
) -> str | None:
    """Rewrite one nested if/elif/else group without adding HTML wrappers."""

    prefix = source_text[: group.start]
    suffix = source_text[group.end :]
    setup_prefix, visible_prefix = _split_rewrite_setup_blocks(prefix)
    prefix_has_text = _contains_translatable_text(prefix)
    suffix_has_words = bool(_visible_words(suffix))
    if _contains_rewrite_unsafe_tail_control(suffix):
        return None
    if not prefix_has_text and not suffix_has_words:
        return None
    if prefix_has_text and _visible_text_for_rewrite(prefix).rstrip().endswith(
        (".", "!", "?", ";")
    ):
        return None
    if not all(
        _is_simple_branch_sentence_fragment(source_text[branch.start : branch.end])
        for branch in group.branches
    ):
        return None

    suffix_after_group = (
        suffix.lstrip() if _jinja_block_trims_following_whitespace(group.end_text) else suffix
    )
    rewritten_parts: list[str] = [setup_prefix]
    for branch in group.branches:
        branch_body = source_text[branch.start : branch.end]
        if _jinja_block_trims_following_whitespace(branch.opener_text):
            branch_body = branch_body.lstrip()
        if branch.rstrip_body:
            branch_body = branch_body.rstrip()
        branch_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=branch_body,
            opener_text=branch.opener_text,
        )
        rewritten_parts.append(branch.opener_text)
        rewritten_parts.append(branch_prefix)
        rewritten_parts.append(branch_body)
        rewritten_parts.append(suffix_after_group)
    if not any(_jinja_block_keyword(branch.opener_text) == "else" for branch in group.branches):
        fallback_opener = group.branches[0].opener_text
        fallback_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=suffix_after_group,
            opener_text=fallback_opener,
        )
        rewritten_parts.append("{% else %}")
        rewritten_parts.append(fallback_prefix)
        rewritten_parts.append(suffix_after_group)
    rewritten_parts.append(group.end_text)
    return "".join(rewritten_parts)


def _rewrite_single_alternative_branch_group(
    *,
    inner_text: str,
    opening_tag: str,
    closing_tag: str,
    group: BranchRewriteGroup,
    active_conditions: list[str],
) -> str | None:
    """Rewrite one if/elif/else group into complete branch sentences."""

    prefix = inner_text[: group.start]
    suffix = inner_text[group.end :]
    setup_prefix, visible_prefix = _split_rewrite_setup_blocks(prefix)
    prefix_has_text = _contains_translatable_text(prefix)
    suffix_has_words = bool(_visible_words(suffix))
    if _contains_rewrite_unsafe_tail_control(suffix):
        return None
    if not prefix_has_text and not suffix_has_words:
        return None
    if prefix_has_text and _visible_text_for_rewrite(prefix).rstrip().endswith(
        (".", "!", "?", ";")
    ):
        return None
    if not all(
        _is_simple_branch_sentence_fragment(inner_text[branch.start : branch.end])
        for branch in group.branches
    ):
        return None

    suffix_after_group = (
        suffix.lstrip() if _jinja_block_trims_following_whitespace(group.end_text) else suffix
    )
    rewritten_parts: list[str] = []
    rewritten_parts.append(setup_prefix)
    for branch in group.branches:
        branch_body = inner_text[branch.start : branch.end]
        if _jinja_block_trims_following_whitespace(branch.opener_text):
            branch_body = branch_body.lstrip()
        if branch.rstrip_body:
            branch_body = branch_body.rstrip()
        branch_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=branch_body,
            opener_text=branch.opener_text,
        )
        rewritten_parts.append(branch.opener_text)
        rewritten_parts.append(opening_tag)
        rewritten_parts.append(branch_prefix)
        rewritten_parts.append(branch_body)
        rewritten_parts.append(suffix_after_group)
        rewritten_parts.append(closing_tag)
    has_explicit_else = any(
        _jinja_block_keyword(branch.opener_text) == "else" for branch in group.branches
    )
    if not has_explicit_else and not _active_truthy_selector_covers_group(
        group=group,
        active_conditions=active_conditions,
    ):
        fallback_opener = group.branches[0].opener_text
        fallback_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=suffix_after_group,
            opener_text=fallback_opener,
        )
        rewritten_parts.append("{% else %}")
        rewritten_parts.append(opening_tag)
        rewritten_parts.append(fallback_prefix)
        rewritten_parts.append(suffix_after_group)
        rewritten_parts.append(closing_tag)
    rewritten_parts.append(group.end_text)
    return "".join(rewritten_parts)


def _active_truthy_selector_covers_group(
    *,
    group: BranchRewriteGroup,
    active_conditions: list[str],
) -> bool:
    """Avoid exposing unreachable enum fallbacks as translator-facing fragments.

    DSW answer branches often look like:

    `{% if answer %}<p>Prefix {% if answer == option_a %}...{% endif %}</p>{% endif %}`.

    The generic rewriter normally adds an `else` fallback to preserve arbitrary
    unknown selector values. For enumerated DSW answers, that fallback renders
    only the prefix (`We will use.`), which is not useful to translate.  If an
    outer condition already checks the same selector for truthiness, we treat the
    inner equality branches as the intended closed option set.
    """

    selector_name = _branch_group_equality_selector_name(group)
    if selector_name is None:
        return False
    return selector_name in {
        _normalize_truthy_condition(condition) for condition in active_conditions
    }


def _branch_group_equality_selector_name(group: BranchRewriteGroup) -> str | None:
    selector_names: set[str] = set()
    for branch in group.branches:
        keyword = _jinja_block_keyword(branch.opener_text)
        if keyword == "else":
            return None
        if keyword not in {"if", "elif"}:
            continue
        condition = _jinja_block_inner(branch.opener_text).split(None, 1)
        if len(condition) != 2:
            return None
        match = re.match(
            r"(?P<selector>[A-Za-z_][A-Za-z0-9_.]*)\s*==\s*.+\Z",
            condition[1],
            flags=re.DOTALL,
        )
        if match is None:
            return None
        selector_names.add(match.group("selector"))
    if len(selector_names) != 1:
        return None
    return next(iter(selector_names))


def _normalize_truthy_condition(condition: str) -> str:
    normalized = condition.strip()
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", normalized):
        return normalized
    return ""


def _rewrite_single_choice_optional_branch_groups(
    *,
    inner_text: str,
    opening_tag: str,
    closing_tag: str,
    active_conditions: list[str],
) -> str | None:
    """Rewrite adjacent optional if fragments when an outer condition guarantees one choice."""

    if not _is_single_choice_context(active_conditions):
        return None

    inner_tokens = _lex_source_tokens(inner_text)
    groups = _collect_top_level_optional_rewrite_groups(tokens=inner_tokens)
    if len(groups) < 2:
        return None
    if not all(len(group.branches) == 1 for group in groups):
        return None

    prefix = inner_text[: groups[0].start]
    suffix = inner_text[groups[-1].end :]
    setup_prefix, visible_prefix = _split_rewrite_setup_blocks(prefix)
    if _contains_rewrite_unsafe_tail_control(suffix):
        return None
    if not _contains_translatable_text(prefix) or not _visible_words(suffix):
        return None
    if _visible_text_for_rewrite(prefix).rstrip().endswith((".", "!", "?", ":", ";")):
        return None
    gaps = [
        inner_text[left.end : right.start] for left, right in zip(groups, groups[1:], strict=False)
    ]
    if any(gap.strip() for gap in gaps):
        return None
    if not all(
        _is_simple_branch_sentence_fragment(
            inner_text[group.branches[0].start : group.branches[0].end]
        )
        for group in groups
    ):
        return None

    rewritten_parts: list[str] = []
    rewritten_parts.append(setup_prefix)
    for index, group in enumerate(groups):
        branch = group.branches[0]
        branch_body = inner_text[branch.start : branch.end]
        if _jinja_block_trims_following_whitespace(branch.opener_text):
            branch_body = branch_body.lstrip()
        if branch.rstrip_body:
            branch_body = branch_body.rstrip()
        branch_prefix = _branch_prefix_for_rewrite(
            visible_prefix=visible_prefix,
            branch_body=branch_body,
            opener_text=branch.opener_text,
        )
        suffix_after_group = (
            suffix.lstrip() if _jinja_block_trims_following_whitespace(group.end_text) else suffix
        )
        rewritten_parts.append(branch.opener_text)
        rewritten_parts.append(opening_tag)
        rewritten_parts.append(branch_prefix)
        rewritten_parts.append("".join(gaps[:index]))
        rewritten_parts.append(branch_body)
        rewritten_parts.append("".join(gaps[index:]))
        rewritten_parts.append(suffix_after_group)
        rewritten_parts.append(closing_tag)
        rewritten_parts.append(group.end_text)
    return "".join(rewritten_parts)


def _split_rewrite_setup_blocks(prefix: str) -> tuple[str, str]:
    """Move non-rendering setup blocks before rewritten branch conditions.

    Some upstream sentences compute a branch selector inside the HTML tag, after
    a shared text prefix. If we duplicate that sentence into if/elif branches,
    the selector must be evaluated before the rewritten branch opener.
    """

    tokens = _lex_source_tokens(prefix)
    setup_parts: list[str] = []
    visible_parts: list[str] = []
    cursor = 0

    for token in tokens:
        if token.kind == "jinja_block" and _is_rewrite_setup_block(token.text):
            segment = prefix[cursor : token.start]
            if _jinja_block_trims_previous_whitespace(token.text):
                segment = segment.rstrip()
            visible_parts.append(segment)
            setup_parts.append(token.text)
            cursor = token.end
            if _jinja_block_trims_following_whitespace(token.text):
                while cursor < len(prefix) and prefix[cursor].isspace():
                    cursor += 1

    visible_parts.append(prefix[cursor:])
    return "".join(setup_parts), "".join(visible_parts)


def _branch_prefix_for_rewrite(
    *,
    visible_prefix: str,
    branch_body: str,
    opener_text: str,
) -> str:
    if not _jinja_block_trims_previous_whitespace(opener_text):
        return visible_prefix

    trimmed_prefix = visible_prefix.rstrip()
    if trimmed_prefix == visible_prefix:
        return trimmed_prefix
    if not _should_restore_single_trimmed_space(trimmed_prefix, branch_body):
        return trimmed_prefix
    return f'{trimmed_prefix}{{{{" "}}}}'


def _should_restore_single_trimmed_space(prefix: str, branch_body: str) -> bool:
    if not prefix or not branch_body:
        return False
    visible_prefix = _visible_text_for_rewrite(prefix)
    visible_branch = _visible_text_for_rewrite(branch_body)
    if not visible_prefix or not visible_branch:
        return False
    if visible_prefix.endswith((".", "!", "?", ";", "(", "[", "{", "/", "-", "–")):
        return False
    return True


def _is_rewrite_setup_block(token_text: str) -> bool:
    inner = _jinja_block_inner(token_text)
    keyword = inner.split(None, 1)[0] if inner else ""
    if keyword == "do":
        return True
    if keyword == "set":
        return "=" in inner
    return False


def _contains_rewrite_unsafe_tail_control(source_text: str) -> bool:
    """Avoid moving branch tails that contain loop-scoped or setup-only code."""

    unsafe_keywords = {"do", "for", "endfor", "set"}
    return any(
        token.kind == "jinja_block" and _jinja_block_keyword(token.text) in unsafe_keywords
        for token in _lex_source_tokens(source_text)
    )


def _jinja_block_trims_following_whitespace(token_text: str) -> bool:
    return token_text.rstrip().endswith("-%}")


def _jinja_block_trims_previous_whitespace(token_text: str) -> bool:
    return token_text.startswith("{%-")


def _restore_branch_sentence_rewrites(source_text: str) -> str:
    """Restore original common-prefix branches when compacting."""

    def replace(match: re.Match[str]) -> str:
        try:
            return base64.urlsafe_b64decode(match.group("payload")).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise TemplateTransformError("Invalid branch sentence rewrite marker") from exc

    return BRANCH_SENTENCE_REWRITE_PATTERN.sub(replace, source_text)


def _collect_top_level_branch_rewrite_groups(
    *, tokens: list[SourceToken]
) -> list[BranchRewriteGroup]:
    return _collect_top_level_rewrite_groups(tokens=tokens, require_alternatives=True)


def _collect_top_level_optional_rewrite_groups(
    *, tokens: list[SourceToken]
) -> list[BranchRewriteGroup]:
    return _collect_top_level_rewrite_groups(tokens=tokens, require_alternatives=False)


def _collect_top_level_rewrite_groups(
    *, tokens: list[SourceToken], require_alternatives: bool
) -> list[BranchRewriteGroup]:
    groups: list[BranchRewriteGroup] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "jinja_block" and _jinja_block_keyword(token.text) == "if":
            parsed_group, end_index = _parse_branch_rewrite_group(
                tokens=tokens,
                start_index=index,
                require_alternatives=require_alternatives,
            )
            if parsed_group is not None:
                groups.append(parsed_group)
                index = end_index + 1
                continue
        index += 1
    return groups


def _parse_branch_rewrite_group(
    *, tokens: list[SourceToken], start_index: int, require_alternatives: bool
) -> tuple[BranchRewriteGroup | None, int]:
    start_token = tokens[start_index]
    depth = 1
    branch_start = start_token.end
    branch_opener = start_token.text
    branches: list[BranchRewriteBranch] = []
    has_alternatives = False

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
                branches.append(
                    BranchRewriteBranch(
                        opener_text=branch_opener,
                        start=branch_start,
                        end=token.start,
                        rstrip_body=token.text.startswith("{%-"),
                    )
                )
                if require_alternatives and not has_alternatives:
                    return None, index
                return (
                    BranchRewriteGroup(
                        start=start_token.start,
                        end=token.end,
                        end_text=token.text,
                        branches=tuple(branches),
                    ),
                    index,
                )
            continue
        if depth == 1 and keyword in {"elif", "else"}:
            has_alternatives = True
            branches.append(
                BranchRewriteBranch(
                    opener_text=branch_opener,
                    start=branch_start,
                    end=token.start,
                    rstrip_body=token.text.startswith("{%-"),
                )
            )
            branch_opener = token.text
            branch_start = token.end

    return None, start_index


def _active_jinja_if_conditions_at(*, tokens: list[SourceToken], token_index: int) -> list[str]:
    """Return the active surrounding Jinja if/elif conditions before one token."""

    conditions: list[str] = []
    for token in tokens[:token_index]:
        if token.kind != "jinja_block":
            continue
        inner = _jinja_block_inner(token.text)
        keyword = inner.split(None, 1)[0] if inner else ""
        if keyword == "if":
            conditions.append(inner.split(None, 1)[1] if " " in inner else "")
        elif keyword == "elif":
            if conditions:
                conditions[-1] = inner.split(None, 1)[1] if " " in inner else ""
        elif keyword == "else":
            if conditions:
                conditions[-1] = "else"
        elif keyword == "endif" and conditions:
            conditions.pop()
    return conditions


def _is_single_choice_context(active_conditions: list[str]) -> bool:
    return any(re.search(r"(^|[^=!<>])==\s*1(\D|$)", condition) for condition in active_conditions)


def _jinja_block_keyword(token_text: str) -> str:
    inner = _jinja_block_inner(token_text)
    return inner.split(None, 1)[0] if inner else ""


def _jinja_block_inner(token_text: str) -> str:
    return token_text[2:-2].strip().strip("-").strip()


def _is_simple_branch_sentence_fragment(source_text: str) -> bool:
    if not (_contains_translatable_text(source_text) or _visible_words(source_text)):
        return False
    tokens = _lex_source_tokens(source_text)
    for token in tokens:
        if token.kind == "jinja_block":
            return False
        if token.kind == "html_tag" and token.tag_name not in {
            "a",
            "em",
            "small",
            "span",
            "strong",
        }:
            return False
    return True


def _visible_text_for_rewrite(source_text: str) -> str:
    stripped = JINJA_EXPR_PATTERN.sub(" {value} ", source_text)
    stripped = JINJA_BLOCK_PATTERN.sub(" ", stripped)
    stripped = re.sub(r"\{#.*?#\}", " ", stripped, flags=re.DOTALL)
    stripped = HTML_TAG_PATTERN.sub(" ", stripped)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def _visible_words(source_text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", _visible_text_for_rewrite(source_text))


def _replace_non_overlapping_regions(
    source_text: str, replacements: list[tuple[int, int, str]]
) -> str:
    parts: list[str] = []
    cursor = 0
    for start, end, replacement in sorted(replacements, key=lambda item: item[0]):
        if start < cursor:
            continue
        parts.append(source_text[cursor:start])
        parts.append(replacement)
        cursor = end
    parts.append(source_text[cursor:])
    return "".join(parts)


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
    return bool(_extract_translatable_jinja_literals(expr))


def _collect_annotation_regions(
    *, tokens: list[SourceToken], source_text: str
) -> list[AnnotationRegion]:
    element_regions = _collect_element_regions(tokens=tokens, source_text=source_text)
    inline_regions = _collect_inline_text_regions(
        tokens=tokens,
        source_text=source_text,
        covered_regions=element_regions,
    )
    return sorted(element_regions + inline_regions, key=lambda item: item.start)


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


def _contains_translatable_text(source_text: str) -> bool:
    stripped = GENERATED_BLOCK_PATTERN.sub(lambda match: generated_block_body(match), source_text)
    stripped = JINJA_EXPR_PATTERN.sub(_replace_expr_with_visible_literals, stripped)
    stripped = JINJA_BLOCK_PATTERN.sub(_replace_block_with_visible_literals, stripped)
    stripped = re.sub(r"\{#.*?#\}", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"\{%.*?%\}", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"\{\{.*?\}\}", "", stripped, flags=re.DOTALL)
    visible_text = html.unescape(HTML_TAG_PATTERN.sub("", stripped))
    return VISIBLE_TEXT_PATTERN.search(visible_text) is not None


def _replace_expr_with_visible_literals(match: re.Match[str]) -> str:
    return " ".join(_extract_translatable_jinja_literals(match.group("expr")))


def _replace_block_with_visible_literals(match: re.Match[str]) -> str:
    return " ".join(_extract_translatable_jinja_block_literals(match.group("body")))


def _is_translatable_jinja_block(token_text: str) -> bool:
    match = JINJA_BLOCK_PATTERN.fullmatch(token_text)
    return bool(match and _extract_translatable_jinja_block_literals(match.group("body")))
