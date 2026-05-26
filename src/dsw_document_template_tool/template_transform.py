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

TOKEN_PATTERN = re.compile(r"(\{#.*?#\}|\{%.*?%\}|\{\{.*?\}\}|</?[A-Za-z][^>]*?>)", re.DOTALL)
JINJA_EXPR_PATTERN = re.compile(r"\{\{\s*(?P<expr>.*?)\s*\}\}", re.DOTALL)
JINJA_BLOCK_PATTERN = re.compile(r"\{%\s*(?P<body>.*?)\s*%\}", re.DOTALL)
JINJA_STRING_LITERAL_PATTERN = re.compile(
    r"(?P<literal>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')",
    re.DOTALL,
)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
HTML_TAG_NAME_PATTERN = re.compile(r"</?\s*([A-Za-z][A-Za-z0-9:-]*)")
VISIBLE_TEXT_PATTERN = re.compile(r"[A-Za-z0-9]")
UUID_LITERAL_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
GENERATED_BLOCK_PATTERN = re.compile(
    r"\{# (?P<marker_name>__tr_block_\d{4}):start #\}"
    r"(?P<marker_body>.*?)"
    r"\{# (?P=marker_name):end #\}"
    r"|"
    r"\{% set (?P<set_name>__tr_block_\d{4}) %\}"
    r"(?P<set_body>.*?)"
    r"\{% endset %\}\{\{ (?P=set_name) \}\}",
    re.DOTALL,
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
MANIFEST_PATH = Path(".transform") / "manifest.json"
MANIFEST_VERSION = 2
UPSTREAM_README_NAME = "UPSTREAM-README.md"
GENERATED_BLOCK_PREFIX = "__tr_block_"
CJK_FONT_PATCH_NAME = "cjk_font_face"
ZH_HANT_ALLOWED_PACKAGE_PATCH_NAME = "zh_hant_allowed_package"
CJK_FONT_SOURCE_PATH = Path("workspace/document-templates/assets/fonts/NotoSansTC-Variable.ttf")
CJK_FONT_TEMPLATE_PATH = Path("src/fonts/NotoSansTC-Variable.ttf")
CJK_FONT_PDF_FORMAT_UUID = "68c26e34-5e77-4e15-9bf7-06ff92582257"
CJK_FONT_FAMILY_ORIGINAL = '"Open Sans", sans-serif'
CJK_FONT_FAMILY_PATCHED = (
    f'{{% if dsw_document_format_uuid == "{CJK_FONT_PDF_FORMAT_UUID}" %}}'
    '"DSW Noto Sans TC", '
    "{% endif %}"
    f"{CJK_FONT_FAMILY_ORIGINAL}"
)
CJK_FONT_CSS_START = "/* DSW Document Template Tool CJK font fallback:start */"
CJK_FONT_CSS_END = "/* DSW Document Template Tool CJK font fallback:end */"
CJK_FONT_CSS = f"""{{% set dsw_document_format_uuid = ctx.document.formatUuid|default("") -%}}
{{% if dsw_document_format_uuid == "{CJK_FONT_PDF_FORMAT_UUID}" -%}}
{{% set dsw_noto_sans_tc_font = assets("{CJK_FONT_TEMPLATE_PATH.as_posix()}") -%}}
{{% if dsw_noto_sans_tc_font -%}}
{CJK_FONT_CSS_START}
@font-face {{
  font-family: "DSW Noto Sans TC";
  src: url("data:font/ttf;base64,{{{{ dsw_noto_sans_tc_font.data_base64 }}}}") format("truetype");
  font-weight: 400;
  font-style: normal;
  unicode-range: U+2E80-2EFF, U+2F00-2FDF, U+3000-303F, U+3100-312F,
    U+31C0-31EF, U+3200-32FF, U+3400-4DBF, U+4E00-9FFF,
    U+F900-FAFF, U+FE10-FE1F, U+FE30-FE4F, U+FF00-FFEF;
}}

@font-face {{
  font-family: "DSW Noto Sans TC";
  src: url("data:font/ttf;base64,{{{{ dsw_noto_sans_tc_font.data_base64 }}}}") format("truetype");
  font-weight: 700;
  font-style: normal;
  unicode-range: U+2E80-2EFF, U+2F00-2FDF, U+3000-303F, U+3100-312F,
    U+31C0-31EF, U+3200-32FF, U+3400-4DBF, U+4E00-9FFF,
    U+F900-FAFF, U+FE10-FE1F, U+FE30-FE4F, U+FF00-FFEF;
}}
{CJK_FONT_CSS_END}
{{% endif -%}}
{{% endif -%}}
"""
ZH_HANT_ALLOWED_PACKAGE_RULE = {
    "orgId": "dsw",
    "kmId": "root-zh-hant",
    "minVersion": "2.7.0",
    "maxVersion": None,
}
ANNOTATABLE_HTML_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "li",
    "dt",
    "dd",
    "th",
    "td",
    "caption",
}
VOID_HTML_TAGS = {
    "br",
    "hr",
    "img",
    "input",
    "meta",
    "link",
    "source",
    "area",
    "base",
    "col",
    "embed",
    "param",
    "track",
    "wbr",
}
JINJA_CONTROL_OPENERS = {
    "if",
    "for",
    "macro",
    "call",
    "filter",
    "block",
    "with",
    "trans",
}
JINJA_CONTROL_CLOSERS = {
    "endif": "if",
    "endfor": "for",
    "endmacro": "macro",
    "endcall": "call",
    "endfilter": "filter",
    "endblock": "block",
    "endwith": "with",
    "endtrans": "trans",
    "endset": "set",
}


@dataclass(frozen=True)
class SourceToken:
    """One lexed template token with original source offsets."""

    kind: str
    text: str
    start: int
    end: int
    tag_name: str | None = None
    is_opening_tag: bool = False
    is_closing_tag: bool = False
    is_self_closing_tag: bool = False


@dataclass(frozen=True)
class AnnotationRegion:
    """One translatable source region in the expanded workspace."""

    start: int
    end: int


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


class TemplateTransformError(RuntimeError):
    """Raised when a template cannot be expanded or compacted safely."""


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
    post_expand_patches = _apply_post_expand_patches(output_dir=output_dir)

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


def snapshot_tree(root_dir: Path) -> dict[str, bytes]:
    """Return one deterministic file snapshot for content comparisons."""

    snapshot: dict[str, bytes] = {}
    for path in sorted(root_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root_dir).as_posix()
        snapshot[relative_path] = path.read_bytes()
    return snapshot


def _build_post_expand_patch_state(*, output_dir: Path) -> dict[str, object]:
    template_json_path = output_dir / "template.json"
    return {
        "template_json_trailing_newline": (
            template_json_path.read_bytes().endswith(b"\n")
            if template_json_path.is_file()
            else None
        )
    }


def _apply_post_expand_patches(*, output_dir: Path) -> list[str]:
    """Apply deterministic local template patches after reversible expansion."""

    patches: list[str] = []
    if _patch_zh_hant_allowed_package(output_dir=output_dir):
        patches.append(ZH_HANT_ALLOWED_PACKAGE_PATCH_NAME)
    if _patch_cjk_font_face(output_dir=output_dir):
        patches.append(CJK_FONT_PATCH_NAME)
    return patches


def _revert_post_expand_patches(
    *,
    output_dir: Path,
    patches: object,
    patch_state: object,
) -> None:
    """Remove local-only patches when compacting back to the upstream template."""

    if not isinstance(patches, list):
        return
    state = patch_state if isinstance(patch_state, dict) else {}
    patch_names = {patch for patch in patches if isinstance(patch, str)}
    if ZH_HANT_ALLOWED_PACKAGE_PATCH_NAME in patch_names:
        _remove_zh_hant_allowed_package(
            output_dir=output_dir,
            trailing_newline=state.get("template_json_trailing_newline"),
        )
    if CJK_FONT_PATCH_NAME in patch_names:
        _remove_cjk_font_face(output_dir=output_dir)


def _patch_zh_hant_allowed_package(*, output_dir: Path) -> bool:
    template_json_path = output_dir / "template.json"
    if not template_json_path.is_file():
        return False
    payload = json.loads(template_json_path.read_text(encoding="utf-8"))
    allowed_packages = payload.get("allowedPackages")
    if not isinstance(allowed_packages, list):
        return False
    if not any(
        _is_allowed_package_rule(rule, org_id="dsw", km_id="root") for rule in allowed_packages
    ):
        return False
    if any(
        _is_allowed_package_rule(rule, org_id="dsw", km_id="root-zh-hant")
        for rule in allowed_packages
    ):
        return False

    allowed_packages.append(dict(ZH_HANT_ALLOWED_PACKAGE_RULE))
    template_json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def _remove_zh_hant_allowed_package(*, output_dir: Path, trailing_newline: object) -> None:
    template_json_path = output_dir / "template.json"
    if not template_json_path.is_file():
        return
    payload = json.loads(template_json_path.read_text(encoding="utf-8"))
    allowed_packages = payload.get("allowedPackages")
    if not isinstance(allowed_packages, list):
        return
    filtered_packages = [
        rule
        for rule in allowed_packages
        if not _is_exact_allowed_package_rule(rule, ZH_HANT_ALLOWED_PACKAGE_RULE)
    ]
    if len(filtered_packages) == len(allowed_packages):
        return
    payload["allowedPackages"] = filtered_packages
    suffix = "\n" if trailing_newline is not False else ""
    template_json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + suffix,
        encoding="utf-8",
    )


def _patch_cjk_font_face(*, output_dir: Path) -> bool:
    style_path = output_dir / "src" / "style.css"
    if not style_path.is_file():
        return False
    style_text = style_path.read_text(encoding="utf-8")
    if CJK_FONT_CSS_START in style_text:
        return False

    font_source_path = _repo_root() / CJK_FONT_SOURCE_PATH
    if not font_source_path.is_file():
        raise TemplateTransformError(
            f"Cannot apply CJK font patch because the font asset is missing: {font_source_path}"
        )

    font_destination_path = output_dir / CJK_FONT_TEMPLATE_PATH
    font_destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(font_source_path, font_destination_path)
    style_text = style_text.replace(CJK_FONT_FAMILY_ORIGINAL, CJK_FONT_FAMILY_PATCHED)
    style_path.write_text(
        _insert_css_after_initial_imports(style_text, CJK_FONT_CSS),
        encoding="utf-8",
    )
    return True


def _remove_cjk_font_face(*, output_dir: Path) -> None:
    style_path = output_dir / "src" / "style.css"
    if style_path.is_file():
        style_text = style_path.read_text(encoding="utf-8")
        style_text = re.sub(
            rf"\{{%\s*set dsw_document_format_uuid\b[\s\S]*?"
            rf"{re.escape(CJK_FONT_CSS_END)}\s*"
            rf"\{{%\s*endif\s*-?%\}}\s*"
            rf"\{{%\s*endif\s*-?%\}}\s*",
            "",
            style_text,
            count=1,
            flags=re.DOTALL,
        )
        style_text = re.sub(
            rf"{re.escape(CJK_FONT_CSS_START)}.*?{re.escape(CJK_FONT_CSS_END)}\n*",
            "",
            style_text,
            count=1,
            flags=re.DOTALL,
        )
        style_text = style_text.replace(CJK_FONT_FAMILY_PATCHED, CJK_FONT_FAMILY_ORIGINAL)
        style_path.write_text(style_text, encoding="utf-8")

    font_destination_path = output_dir / CJK_FONT_TEMPLATE_PATH
    font_destination_path.unlink(missing_ok=True)
    fonts_dir = font_destination_path.parent
    if fonts_dir.is_dir() and not any(fonts_dir.iterdir()):
        fonts_dir.rmdir()


def _is_allowed_package_rule(rule: object, *, org_id: str, km_id: str) -> bool:
    return isinstance(rule, dict) and rule.get("orgId") == org_id and rule.get("kmId") == km_id


def _is_exact_allowed_package_rule(rule: object, expected: dict[str, object]) -> bool:
    return (
        isinstance(rule, dict)
        and rule.get("orgId") == expected["orgId"]
        and rule.get("kmId") == expected["kmId"]
        and rule.get("minVersion") == expected["minVersion"]
        and rule.get("maxVersion") == expected["maxVersion"]
    )


def _insert_css_after_initial_imports(style_text: str, css_block: str) -> str:
    lines = style_text.splitlines(keepends=True)
    insert_at = 0
    while insert_at < len(lines):
        stripped = lines[insert_at].strip()
        if stripped.startswith("@charset") or stripped.startswith("@import"):
            insert_at += 1
            continue
        if not stripped:
            insert_at += 1
            continue
        break

    return "".join([*lines[:insert_at], css_block, "\n", *lines[insert_at:]])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _expand_template_text(*, source_text: str) -> str:
    source_text = _rewrite_append_sentence_literals(source_text)
    source_text = _rewrite_known_science_europe_source_fragments(source_text)
    source_text = _rewrite_inline_conditional_expressions(source_text)
    source_text = _rewrite_common_prefix_branch_sentences(source_text)
    source_text = _rewrite_known_science_europe_fragments(source_text)
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


def _apply_reversible_replacements(
    source_text: str,
    replacements: tuple[tuple[str, str], ...],
) -> str:
    rewritten_text = source_text
    for original, replacement in replacements:
        if original not in rewritten_text:
            continue
        rewritten_text = rewritten_text.replace(
            original,
            _wrap_reversible_branch_sentence_rewrite(
                original=original,
                replacement=replacement,
            ),
            1,
        )
    return rewritten_text


def _rewrite_known_science_europe_source_fragments(source_text: str) -> str:
    """Rewrite exact upstream Science Europe fragments before generic expansion."""

    ref_data_conditions_original = """
            {%- if refDataConditionsReply %}
             <p>This standard reference data are{{+" "}}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                freely available for any use.
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                freely available with obligation to quote the source.
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                available with {{" "}}
                  {%- if refDataConditionsOtherRepl -%}
                    following restrictions: "{{refDataConditionsOtherRepl}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
             </p>
            {%- endif -%}
"""
    ref_data_conditions_replacement = """
            {%- if refDataConditionsReply %}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                <p>This standard reference data are{{+" "}}freely available for any use.</p>
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                <p>This standard reference data are{{+" "}}freely available with obligation to quote the source.</p>
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                {%- if refDataConditionsOtherRepl -%}
                  <p>This standard reference data are{{+" "}}available with following restrictions: "{{refDataConditionsOtherRepl}}".</p>
                {%- else -%}
                  <p>This standard reference data are{{+" "}}available with restrictions, that will be specified.</p>
                {%- endif -%}
              {%- endif -%}
            {%- endif -%}
"""

    nref_data_conditions_original = """
          {%- if nrefDataConditionsReply %}
            <p>This data are{{+" "}}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              freely available for any use.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              freely available with obligation to quote the source.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                available with{{" "}}
                  {%- if nrefDataConditionsOtherReply -%}
                   following restrictions: "{{nrefDataConditionsOtherReply}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
            {%- endif -%}
            </p>
          {%- endif -%}
"""
    nref_data_conditions_replacement = """
          {%- if nrefDataConditionsReply %}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              <p>This data are{{+" "}}freely available for any use.</p>
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              <p>This data are{{+" "}}freely available with obligation to quote the source.</p>
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                <p>This data are{{+" "}}available with following restrictions: "{{nrefDataConditionsOtherReply}}".</p>
              {%- else -%}
                <p>This data are{{+" "}}available with restrictions, that will be specified.</p>
              {%- endif -%}
            {%- endif -%}
          {%- endif -%}
"""

    nref_personal_legal_basis_original = """
          <p>
            This data include personal data
            {%- set nrefDataPersonalLegalBasis = [nrefDataPersonal, uuids.nrefDataPersonalYesAUuid, uuids.nrefDataPersonalLegalBasisQUuid]|reply_path -%}
            {%- set nrefDataPersonalLegalBasisReply = repliesMap[nrefDataPersonalLegalBasis]|reply_str_value -%}
            {%- if nrefDataPersonalLegalBasisReply -%}
              , legaly based on{{+" "}}
              {%- if nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisPubInterestAUuid -%}
                public interest for processing the data under GDPR.
              {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisConsentAUuid -%}
                consent given by the research subject for processing the data under GDPR
                {%- set nrefDataPersonalLegalBasisReuse = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLegalBasisConsentAUuid, uuids.nrefDataPersonalLegalBasisConsentReuseQUuid]|reply_path -%}
                {%- set nrefDataPersonalLegalBasisReuseReply = repliesMap[nrefDataPersonalLegalBasisReuse]|reply_str_value -%}
                {%- if nrefDataPersonalLegalBasisReuseReply -%}
                  , which{{+" "}}
                  {%- if nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseYesAUuid -%}
                    covers also our reuse.
                  {%- elif nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseNoAUuid -%}
                    does not cover our reuse; therefore, new consent will be needed.
                  {%- endif -%}
                {%- else -%}
                .
                {%- endif -%}
              {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLebalBasisOtherAUuid -%}
                {%- set nrefDataPersonalLegalBasisOther = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLebalBasisOtherAUuid, uuids.nrefDataPersonalLegalBasisOtherQUuid]|reply_path -%}
                {%- set nrefDataPersonalLegalBasisOtherReply = repliesMap[nrefDataPersonalLegalBasisOther]|reply_str_value -%}
                {%- if nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegalAUuid -%}
                  a legal requirement (meaning a legal obligation to do this data processing).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherVitalAUuid -%}
                  a vital interest (meaning it needs to be done to protect the vital interests of the data subject).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegitAUuid -%}
                  a legitimate interest (meaning data subjects all expect us to do this data processing because of who we are).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherContractAUuid -%}
                  a requirement to fulfill our contract with the data subjects.
                {%- endif -%}
              {%- endif -%} 
            {%- endif -%}
          </p>
"""
    nref_personal_legal_basis_replacement = """
          {%- set nrefDataPersonalLegalBasis = [nrefDataPersonal, uuids.nrefDataPersonalYesAUuid, uuids.nrefDataPersonalLegalBasisQUuid]|reply_path -%}
          {%- set nrefDataPersonalLegalBasisReply = repliesMap[nrefDataPersonalLegalBasis]|reply_str_value -%}
          {%- if nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisPubInterestAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}public interest for processing the data under GDPR.</p>
          {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisConsentAUuid -%}
            {%- set nrefDataPersonalLegalBasisReuse = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLegalBasisConsentAUuid, uuids.nrefDataPersonalLegalBasisConsentReuseQUuid]|reply_path -%}
            {%- set nrefDataPersonalLegalBasisReuseReply = repliesMap[nrefDataPersonalLegalBasisReuse]|reply_str_value -%}
            {%- if nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseYesAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}consent given by the research subject for processing the data under GDPR, which{{+" "}}covers also our reuse.</p>
            {%- elif nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseNoAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}consent given by the research subject for processing the data under GDPR, which{{+" "}}does not cover our reuse; therefore, new consent will be needed.</p>
            {%- else -%}
              <p>This data include personal data, legaly based on{{+" "}}consent given by the research subject for processing the data under GDPR.</p>
            {%- endif -%}
          {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLebalBasisOtherAUuid -%}
            {%- set nrefDataPersonalLegalBasisOther = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLebalBasisOtherAUuid, uuids.nrefDataPersonalLegalBasisOtherQUuid]|reply_path -%}
            {%- set nrefDataPersonalLegalBasisOtherReply = repliesMap[nrefDataPersonalLegalBasisOther]|reply_str_value -%}
            {%- if nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegalAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a legal requirement (meaning a legal obligation to do this data processing).</p>
            {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherVitalAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a vital interest (meaning it needs to be done to protect the vital interests of the data subject).</p>
            {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegitAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a legitimate interest (meaning data subjects all expect us to do this data processing because of who we are).</p>
            {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherContractAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a requirement to fulfill our contract with the data subjects.</p>
            {%- else -%}
              <p>This data include personal data.</p>
            {%- endif -%}
          {%- else -%}
            <p>This data include personal data.</p>
          {%- endif -%}
"""

    computer_readable_original = """
    {%- if dataCompReadReply == uuids.dataCompReadYesAUuid -%}
      <p>We will need to (re-)made the data into computer readable form before their using

      {%- set dataCompReadItself = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadItselfQUuid]|reply_path -%}
      {%- set dataCompReadItselfReply = repliesMap[dataCompReadItself]|reply_str_value -%}
      {%- set dataCompReadOthers = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadOthersQUuid]|reply_path  -%}
      {%- set dataCompReadOthersReply = repliesMap[dataCompReadOthers]|reply_str_value -%}

      {%- if dataCompReadItselfReply -%}
        {%- if dataCompReadItselfReply == uuids.dataCompReadItselfYesAUuid -%}
          {{+" "}}and we will make this computer readable form available to others through a standard repository
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfYesOtherAUuid -%} 
          {{+" "}}and we will make this computer readable form available to others
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfNoAUuid -%}
          {{+" "}}but we won't make this computer readable form available to others
        {%- endif -%}
      {%- endif -%}
      .

      {%- if dataCompReadOthersReply -%}
        {%- if dataCompReadOthersReply == uuids.dataCompReadOthersYesAUuid %}
            We will provide machine readable, standardized metadata to others
            {%- set dataCompReadWhichMetadataStandardPath = [dataCompReadOthers, uuids.dataCompReadOthersYesAUuid, uuids.dataCompReadOthersYesStandardsQUuid]|reply_path -%}
            {%- set dataCompReadMetadataStandardItems =  repliesMap[dataCompReadWhichMetadataStandardPath]|reply_items -%}
            {%- if dataCompReadMetadataStandardItems|length  > 0 -%}
              {{+" "}}and we will use following Metadata Standards:{{+" "}}
                {%- for dataCompReadMetadataStandardItem in dataCompReadMetadataStandardItems -%}
                  {%- set dataCompReadMetadataStandardPrefix = [dataCompReadWhichMetadataStandardPath, dataCompReadMetadataStandardItem]|reply_path -%}
                  {%- set dataCompReadMetadataStandard = [dataCompReadMetadataStandardPrefix, uuids.dataCompReadOthersYesStandardQUuid]|reply_path -%}
                  {%- set dataCompReadMetadataStandardReply = repliesMap[dataCompReadMetadataStandard] -%}
                  {{ macros.integrationFairSharing(dataCompReadMetadataStandardReply) }}{{ ", " if not loop.last else "." }}
                {%- endfor -%}
            {%- else -%}
            .
            {%- endif -%}

        {%- endif -%}
          
      {%- endif -%}
      </p>
    {%- endif -%}
"""
    computer_readable_replacement = """
    {%- if dataCompReadReply == uuids.dataCompReadYesAUuid -%}
      <p>
      {%- set dataCompReadItself = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadItselfQUuid]|reply_path -%}
      {%- set dataCompReadItselfReply = repliesMap[dataCompReadItself]|reply_str_value -%}
      {%- set dataCompReadOthers = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadOthersQUuid]|reply_path  -%}
      {%- set dataCompReadOthersReply = repliesMap[dataCompReadOthers]|reply_str_value -%}

      {%- if dataCompReadItselfReply == uuids.dataCompReadItselfYesAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}and we will make this computer readable form available to others through a standard repository.
      {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfYesOtherAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}and we will make this computer readable form available to others.
      {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfNoAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}but we won't make this computer readable form available to others.
      {%- else -%}
        We will need to (re-)made the data into computer readable form before their using.
      {%- endif -%}

      {%- if dataCompReadOthersReply == uuids.dataCompReadOthersYesAUuid %}
        {%- set dataCompReadWhichMetadataStandardPath = [dataCompReadOthers, uuids.dataCompReadOthersYesAUuid, uuids.dataCompReadOthersYesStandardsQUuid]|reply_path -%}
        {%- set dataCompReadMetadataStandardItems =  repliesMap[dataCompReadWhichMetadataStandardPath]|reply_items -%}
        {%- if dataCompReadMetadataStandardItems|length  > 0 -%}
          {{+" "}}We will provide machine readable, standardized metadata to others{{+" "}}and we will use following Metadata Standards:{{+" "}}
          {%- for dataCompReadMetadataStandardItem in dataCompReadMetadataStandardItems -%}
            {%- set dataCompReadMetadataStandardPrefix = [dataCompReadWhichMetadataStandardPath, dataCompReadMetadataStandardItem]|reply_path -%}
            {%- set dataCompReadMetadataStandard = [dataCompReadMetadataStandardPrefix, uuids.dataCompReadOthersYesStandardQUuid]|reply_path -%}
            {%- set dataCompReadMetadataStandardReply = repliesMap[dataCompReadMetadataStandard] -%}
            {{ macros.integrationFairSharing(dataCompReadMetadataStandardReply) }}{{ ", " if not loop.last else "." }}
          {%- endfor -%}
        {%- else -%}
          {{+" "}}We will provide machine readable, standardized metadata to others.
        {%- endif -%}
      {%- endif -%}
      </p>
    {%- endif -%}
"""

    ref_data_used_identification_original = """
            <p>We will re-use this standard reference data
            {%- if refDataWhere -%}
              {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere }}
             {%- endif -%}
            {%- endif -%}
    
            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataUsageReply -%}
                {{+" "}}in order to "{{ refDataUsageReply}}"
            {%- endif -%}
            .</p>
"""
    ref_data_used_identification_replacement = """
            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataWhere -%}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                {%- if refDataUsageReply -%}
                  <p>We will re-use this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>{{+" "}}in order to "{{ refDataUsageReply}}".</p>
                {%- else -%}
                  <p>We will re-use this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.</p>
                {%- endif -%}
              {%- else -%}
                {%- if refDataUsageReply -%}
                  <p>We will re-use this standard reference data available via:{{" "}}{{ refDataWhere }}{{+" "}}in order to "{{ refDataUsageReply}}".</p>
                {%- else -%}
                  <p>We will re-use this standard reference data available via:{{" "}}{{ refDataWhere }}.</p>
                {%- endif -%}
              {%- endif -%}
            {%- elif refDataUsageReply -%}
              <p>We will re-use this standard reference data in order to "{{ refDataUsageReply}}".</p>
            {%- else -%}
              <p>We will re-use this standard reference data.</p>
            {%- endif -%}
"""

    nref_data_used_identification_original = """
          <p>We will re-use this non-referece data 
          {%- if nrefDataWhere -%}
         {{" "}} available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}
    
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataUsageReply -%}
            {{+" "}}in order to "{{ nrefDataUsageReply}}"
          {%- endif -%}
          .</p>
"""
    nref_data_used_identification_replacement = """
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataWhere -%}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>{{+" "}}in order to "{{ nrefDataUsageReply}}".</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.</p>
              {%- endif -%}
            {%- else -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}{{+" "}}in order to "{{ nrefDataUsageReply}}".</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}.</p>
              {%- endif -%}
            {%- endif -%}
          {%- elif nrefDataUsageReply -%}
            <p>We will re-use this non-referece data in order to "{{ nrefDataUsageReply}}".</p>
          {%- else -%}
            <p>We will re-use this non-referece data.</p>
          {%- endif -%}
"""

    ref_data_not_used_identification_original = """
            <p> We considered reusing this standard reference data
            {%- if refDataWhere -%}
            {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere}}
              {%- endif -%}
            {%- endif -%}

            {# no usage reason #}
            {%- if refDataUseNoReply -%}
              , but decided not to re-use it
              {%- if refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
                {{" "}}because it misses data we need
              {%- elif refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
                {{" "}}because it misses required aspects
              {%- elif refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
                {{" "}}because it is not sufficient quality
              {%- elif refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
                {{" "}}because its conditions of use do not allow us to use it
              {%- elif refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
                {{" "}}because: "{{refDataUseNoOtherReasonReply}}"
              {%- endif -%}
              .
            {%- else -%}
            . </p>
            {%- endif -%}
"""
    ref_data_not_used_identification_replacement = """
            <p>
            {# no usage reason #}
            {%- if refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because it misses data we need.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because it misses required aspects.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because it is not sufficient quality.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because its conditions of use do not allow us to use it.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because: "{{refDataUseNoOtherReasonReply}}".
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because it misses data we need.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because it misses required aspects.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because it is not sufficient quality.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because its conditions of use do not allow us to use it.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because: "{{refDataUseNoOtherReasonReply}}".
            {%- elif refDataWhere and refDataUseNoReply -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it.
            {%- elif refDataWhere -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}.
            {%- elif refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because it misses data we need.
            {%- elif refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because it misses required aspects.
            {%- elif refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because it is not sufficient quality.
            {%- elif refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because its conditions of use do not allow us to use it.
            {%- elif refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because: "{{refDataUseNoOtherReasonReply}}".
            {%- elif refDataUseNoReply -%}
              We considered reusing this standard reference data, but decided not to re-use it.
            {%- else -%}
              We considered reusing this standard reference data.
            {%- endif -%}
            </p>
"""

    nref_data_not_used_identification_original = """
          <p>We considered reusing this non-reference data 
          {%- if nrefDataWhere -%}
          {{+" "}}available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}

          {# no usage reason #}
          {%- if nrefDataUseNoReply -%}
            , but decided not to reuse it
            {%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
              {{" "}}because it misses data we need
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
              {{" "}}becauseit misses required aspects
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
              {{" "}}becauseit is not sufficient quality
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
              {{" "}}because its conditions of use do not allow us to use it
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
              {{" "}}because: "{{nrefDataUseNoOtherReasonReply}}"
            {%- endif -%}
            .
          {%- else -%}
          .</p>
          {%- endif -%}
"""
    nref_data_not_used_identification_replacement = """
          <p>
          {# no usage reason #}
          {%- if nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}because it misses data we need.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}becauseit misses required aspects.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}becauseit is not sufficient quality.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}because its conditions of use do not allow us to use it.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}".
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}because it misses data we need.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}becauseit misses required aspects.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}becauseit is not sufficient quality.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}because its conditions of use do not allow us to use it.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}".
          {%- elif nrefDataWhere and nrefDataUseNoReply -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it.
          {%- elif nrefDataWhere -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}because it misses data we need.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}becauseit misses required aspects.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}becauseit is not sufficient quality.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}because its conditions of use do not allow us to use it.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}".
          {%- elif nrefDataUseNoReply -%}
            We considered reusing this non-reference data, but decided not to reuse it.
          {%- else -%}
            We considered reusing this non-reference data.
          {%- endif -%}
          </p>
"""

    shared_workspace_original = """
    {%- if sharedWorkspaceReply == uuids.sharedWorkspaceYesAUuid and sharedWorkspaceReliablePreventLossReply -%}
     <p>During the project we will use shared working space to work with our data{{+" "}}
      {%- if sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossSufficientAUuid  -%}
        that ensures the prevention of complete data loss.
      {%- elif sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossStoredAUuid -%}
        but we will store all essential data elsewhere.
      {%- endif -%}

      {%- set sharedWorkspaceReliableBackupQUuid = [sharedWorkspaceReliableAUuid, uuids.sharedReliableBackupQUuid]|reply_path -%}
      {%- set sharedWorkspaceReliableBackupReply = repliesMap[sharedWorkspaceReliableBackupQUuid]|reply_str_value  -%}
      {%- if sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyAllSomewhereAUuid -%}
        {{+" "}}And all the data that are stores elsewhere is adequately backed up.
      {%- elif sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyBackupsAUuid -%}
        {{+" "}}We make (automated) backups of all data stored outside of the working area.
      {%- endif -%}
     </p>

    {%- endif -%}
"""
    shared_workspace_replacement = """
    {%- if sharedWorkspaceReply == uuids.sharedWorkspaceYesAUuid and sharedWorkspaceReliablePreventLossReply -%}
     <p>
      {%- if sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossSufficientAUuid  -%}
        During the project we will use shared working space to work with our data{{+" "}}that ensures the prevention of complete data loss.
      {%- elif sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossStoredAUuid -%}
        During the project we will use shared working space to work with our data{{+" "}}but we will store all essential data elsewhere.
      {%- endif -%}

      {%- set sharedWorkspaceReliableBackupQUuid = [sharedWorkspaceReliableAUuid, uuids.sharedReliableBackupQUuid]|reply_path -%}
      {%- set sharedWorkspaceReliableBackupReply = repliesMap[sharedWorkspaceReliableBackupQUuid]|reply_str_value  -%}
      {%- if sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyAllSomewhereAUuid -%}
        {{+" "}}And all the data that are stores elsewhere is adequately backed up.
      {%- elif sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyBackupsAUuid -%}
        {{+" "}}We make (automated) backups of all data stored outside of the working area.
      {%- endif -%}
     </p>

    {%- endif -%}
"""

    published_software_original = """
                            {%- for swItem in isPublishedSwItems -%}
                                {%- set swNameUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatNameQUuid]|reply_path -%}
                                {%- set swNameReply = repliesMap[swNameUuid]|reply_str_value -%}
                                {%- set swPIDUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatPIDQUuid]|reply_path -%}
                                {%- set swPIDReply = repliesMap[swPIDUuid]|reply_str_value -%}
                                <p><strong>{{ swNameReply if swNameReply else "(no name given)" }}</strong>
                                {%- if swPIDReply -%}
                                , available at {{swPIDReply|dot}}</p>
                                {%- else -%}
                                .
                                {%- endif -%}
                            {%- endfor -%}
"""
    published_software_replacement = """
                            {%- for swItem in isPublishedSwItems -%}
                                {%- set swNameUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatNameQUuid]|reply_path -%}
                                {%- set swNameReply = repliesMap[swNameUuid]|reply_str_value -%}
                                {%- set swPIDUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatPIDQUuid]|reply_path -%}
                                {%- set swPIDReply = repliesMap[swPIDUuid]|reply_str_value -%}
                                {%- if swNameReply -%}
                                  {%- set swDisplayName = swNameReply -%}
                                {%- else -%}
                                  {%- set swDisplayName = "(no name given)" -%}
                                {%- endif -%}
                                {%- if swPIDReply -%}
                                <p><strong>{{ swDisplayName }}</strong>, available at {{swPIDReply|dot}}</p>
                                {%- else -%}
                                <p><strong>{{ swDisplayName }}</strong>.</p>
                                {%- endif -%}
                            {%- endfor -%}
"""

    return _apply_reversible_replacements(
        source_text,
        (
            (ref_data_conditions_original, ref_data_conditions_replacement),
            (nref_data_conditions_original, nref_data_conditions_replacement),
            (nref_personal_legal_basis_original, nref_personal_legal_basis_replacement),
            (computer_readable_original, computer_readable_replacement),
            (ref_data_used_identification_original, ref_data_used_identification_replacement),
            (nref_data_used_identification_original, nref_data_used_identification_replacement),
            (
                ref_data_not_used_identification_original,
                ref_data_not_used_identification_replacement,
            ),
            (
                nref_data_not_used_identification_original,
                nref_data_not_used_identification_replacement,
            ),
            (shared_workspace_original, shared_workspace_replacement),
            (published_software_original, published_software_replacement),
        ),
    )


def _rewrite_known_science_europe_fragments(source_text: str) -> str:
    """Patch upstream Science Europe sentence fragments that generic HTML cannot see.

    A few upstream fragments live inside large, unbalanced list-item wrappers, so
    the generic paragraph rewriter cannot safely discover their `<p>` boundaries.
    These replacements are still reversible: compacting restores the exact
    upstream text stored in the marker payload.
    """

    nref_where_url_if = (
        '{%- if nrefDataWhere.startswith("http://") or '
        'nrefDataWhere.startswith("https://") or '
        'nrefDataWhere.startswith("ftp://") -%}'
    )
    nref_no_reason_other_elif = (
        "{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid "
        "and nrefDataUseNoOtherReasonReply -%}"
    )
    nref_no_cond_sentence = (
        ', but decided not to reuse it{{" "}}because its conditions of use do not allow us '
        "to use it"
    )
    nref_no_reason_other_sentence = (
        ', but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}"'
    )
    nref_where_link = (
        '{{+" "}}available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">'
        "{{ nrefDataWhere }} </a>."
    )
    nref_used_where_url_if = (
        '{%- if nrefDataWhere.startswith("http://") or '
        'nrefDataWhere.startswith("https://") or '
        'nrefDataWhere.startswith("ftp://") -%}'
    )
    nref_used_where_link = (
        '{{" "}} available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">'
        "{{ nrefDataWhere }} </a>."
    )

    personal_data_legal_basis_original = """
                    <p> We are collecting and processing personal data{{+" "}}
                    {%- if personalDataLegalBasisReply == uuids.cpersGdprLegalBasisPublicAUuid -%}
                        based on public interest.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisAskAUuid -%}
                        based on subject's consent.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisOtherAUuid -%}
                        {%- set personalDataLegalBasisOtherQUuid = [personalDataLegalBasisQUuid, uuids.cpersGdprLegalBasisOtherAUuid, uuids. cpersGdprLegalBasisOtherWhichQUuid ]|reply_path -%}
                        {%- set personalDataLegalBasisOtherReply = repliesMap[personalDataLegalBasisOtherQUuid]|reply_str_value  -%}
                        {%- if personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichContractAUui -%}
                            in order to fulfil contract.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegitAUuid -%}
                            based on legitimate interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichVitalAUuid -%}
                            based on vital interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegalAUuid -%}
                            based on legal requirement.</p>
                        {%- endif -%}
                    {%- endif -%}
"""
    personal_data_legal_basis_replacement = """
                    {%- if personalDataLegalBasisReply == uuids.cpersGdprLegalBasisPublicAUuid -%}
                        <p> We are collecting and processing personal data{{+" "}}based on public interest.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisAskAUuid -%}
                        <p> We are collecting and processing personal data{{+" "}}based on subject's consent.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisOtherAUuid -%}
                        {%- set personalDataLegalBasisOtherQUuid = [personalDataLegalBasisQUuid, uuids.cpersGdprLegalBasisOtherAUuid, uuids. cpersGdprLegalBasisOtherWhichQUuid ]|reply_path -%}
                        {%- set personalDataLegalBasisOtherReply = repliesMap[personalDataLegalBasisOtherQUuid]|reply_str_value  -%}
                        {%- if personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichContractAUui -%}
                            <p> We are collecting and processing personal data{{+" "}}in order to fulfil contract.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegitAUuid -%}
                            <p> We are collecting and processing personal data{{+" "}}based on legitimate interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichVitalAUuid -%}
                            <p> We are collecting and processing personal data{{+" "}}based on vital interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegalAUuid -%}
                            <p> We are collecting and processing personal data{{+" "}}based on legal requirement.</p>
                        {%- else -%}
                            <p> We are collecting and processing personal data{%- if false -%}</p>{%- endif -%}
                        {%- endif -%}
                    {%- endif -%}
"""

    copyright_open_reasons_original = """
      {%- if nReasons > 0 -%}
        <p>
        The data cannot become completely open because 
        {%- if nReasons == 1 -%}
          {%- if legalReasons %}
            of legal reasons.
          {%- elif businessReasonsPatents %}
            of patent-related business reasons.
          {%- elif businessReasonsOther %}
            of non-patent business reasons{{  ": " ~ notOpenBusinessReasonsOther|dot if notOpenBusinessReasonsOther else "." }}
          {%- elif otherReasonsPapers %}
            we want to publish a paper first.
          {%- elif otherReasonsOther %}
            we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|dot if notOpenOtherReasonsOther else "." }}
          {%- endif -%}
        {%- else %}
          of:
          <ul>
            {%- if legalReasons %}
              <li>legal reasons</li>
            {%- endif -%}
            {%- if businessReasonsPatents %}
              <li>patent-related business reasons</li>
            {%- elif businessReasonsOther %}
              <li>non-patent business reasons{{ ": " ~ notOpenBusinessReasonsOther if notOpenBusinessReasonsOther else "" }}</li>
            {%- endif -%}
            {%- if otherReasonsPapers %}
              <li>we want to publish a paper first</li>
            {%- elif otherReasonsOther -%}
              <li>we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther if notOpenOtherReasonsOther else "" }}</li>
            {%- endif -%}
          </ul>
        {%- endif -%}
"""
    copyright_open_reasons_replacement = """
      {%- if nReasons > 0 -%}
        <p>
        {%- if nReasons == 1 -%}
          {%- if legalReasons %}
            The data cannot become completely open because of legal reasons.
          {%- elif businessReasonsPatents %}
            The data cannot become completely open because of patent-related business reasons.
          {%- elif businessReasonsOther %}
            The data cannot become completely open because of non-patent business reasons{{  ": " ~ notOpenBusinessReasonsOther|dot if notOpenBusinessReasonsOther else "." }}
          {%- elif otherReasonsPapers %}
            The data cannot become completely open because we want to publish a paper first.
          {%- elif otherReasonsOther %}
            The data cannot become completely open because we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|dot if notOpenOtherReasonsOther else "." }}
          {%- endif -%}
        {%- else %}
          The data cannot become completely open because of:
          <ul>
            {%- if legalReasons %}
              <li>legal reasons</li>
            {%- endif -%}
            {%- if businessReasonsPatents %}
              <li>patent-related business reasons</li>
            {%- elif businessReasonsOther %}
              <li>non-patent business reasons{{ ": " ~ notOpenBusinessReasonsOther if notOpenBusinessReasonsOther else "" }}</li>
            {%- endif -%}
            {%- if otherReasonsPapers %}
              <li>we want to publish a paper first</li>
            {%- elif otherReasonsOther -%}
              <li>we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther if notOpenOtherReasonsOther else "" }}</li>
            {%- endif -%}
          </ul>
        {%- endif -%}
"""

    measured_reuse_other_field_original = """
                <p>Researchers working in other fields will be interested in re-using this data
                
                {%- if measuredDataReuseOtherFieldHowReply -%}
                
                 {{" "}}because: {{measuredDataReuseOtherFieldHowReply|dot}}</p>
                {%- else -%}
                .
                {%- endif -%}
"""
    measured_reuse_other_field_replacement = """
                {%- if measuredDataReuseOtherFieldHowReply -%}
                <p>Researchers working in other fields will be interested in re-using this data{{" "}}because: {{measuredDataReuseOtherFieldHowReply|dot}}</p>
                {%- else -%}
                <p>Researchers working in other fields will be interested in re-using this data.</p>
                {%- endif -%}
"""

    replacements = (
        (personal_data_legal_basis_original, personal_data_legal_basis_replacement),
        (copyright_open_reasons_original, copyright_open_reasons_replacement),
        (measured_reuse_other_field_original, measured_reuse_other_field_replacement),
        (
            f"""
         {{{{" "}}}} available via:{{{{" "}}}}
            {nref_used_where_url_if}
              <a href="{{{{ nrefDataWhere }}}}" target="_blank">{{{{ nrefDataWhere }}}} </a>.
            {{%- else -%}}
              {{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
            f"""
            {nref_used_where_url_if}
         {nref_used_where_link}
            {{%- else -%}}
         {{{{" "}}}} available via:{{{{" "}}}}{{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
        ),
        (
            f"""
          {{{{+" "}}}}available via:{{{{" "}}}}
            {nref_where_url_if}
              <a href="{{{{ rnefDataWhere }}}}" target="_blank">{{{{ nrefDataWhere }}}} </a>.
            {{%- else -%}}
              {{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
            f"""
            {nref_where_url_if}
          {nref_where_link}
            {{%- else -%}}
          {{{{+" "}}}}available via:{{{{" "}}}}{{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
        ),
        (
            """
                available with{{" "}}
                  {%- if nrefDataConditionsOtherReply -%}
                   following restrictions: "{{nrefDataConditionsOtherReply}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
""",
            """
                  {%- if nrefDataConditionsOtherReply -%}
                available with{{" "}}following restrictions: "{{nrefDataConditionsOtherReply}}".
                  {%- else -%}
                available with{{" "}}restrictions, that will be specified.
                  {%- endif -%}
""",
        ),
        (
            f"""
            , but decided not to reuse it
            {{%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}}
              {{{{" "}}}}because it misses data we need
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}}
              {{{{" "}}}}becauseit misses required aspects
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}}
              {{{{" "}}}}becauseit is not sufficient quality
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}}
              {{{{" "}}}}because its conditions of use do not allow us to use it
            {nref_no_reason_other_elif}
              {{{{" "}}}}because: "{{{{nrefDataUseNoOtherReasonReply}}}}"
            {{%- endif -%}}
            .
""",
            f"""
            {{%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}}
            , but decided not to reuse it{{{{" "}}}}because it misses data we need.
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}}
            , but decided not to reuse it{{{{" "}}}}becauseit misses required aspects.
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}}
            , but decided not to reuse it{{{{" "}}}}becauseit is not sufficient quality.
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}}
            {nref_no_cond_sentence}.
            {nref_no_reason_other_elif}
            {nref_no_reason_other_sentence}.
            {{%- else -%}}
            , but decided not to reuse it.
            {{%- endif -%}}
""",
        ),
    )

    rewritten_text = source_text
    for original, replacement in replacements:
        if original not in rewritten_text:
            continue
        rewritten_text = rewritten_text.replace(
            original,
            _wrap_reversible_branch_sentence_rewrite(
                original=original,
                replacement=replacement,
            ),
            1,
        )
    return rewritten_text


def _wrap_reversible_branch_sentence_rewrite(*, original: str, replacement: str) -> str:
    encoded_original = base64.urlsafe_b64encode(original.encode("utf-8")).decode("ascii")
    return (
        f"{{# __tr_branch_sentence_original:{encoded_original} #}}"
        f"{replacement}"
        "{# __tr_branch_sentence_original:end #}"
    )


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


def generated_block_name(match: re.Match[str]) -> str:
    """Return the generated block id for marker and legacy set-capture wrappers."""

    return match.group("marker_name") or match.group("set_name")


def generated_block_body(match: re.Match[str]) -> str:
    """Return the wrapped source body for marker and legacy set-capture wrappers."""

    return match.group("marker_body") if match.group("marker_name") else match.group("set_body")


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


def _find_matching_tag_end(*, tokens: list[SourceToken], start_index: int) -> int | None:
    start_token = tokens[start_index]
    tag_name = start_token.tag_name
    if tag_name is None:
        return None

    html_depth = 1
    control_stack: list[str] = []
    saw_inner_control = False
    saw_branch_local_close = False

    for index in range(start_index + 1, len(tokens)):
        token = tokens[index]
        if token.kind == "jinja_block":
            control_event = _classify_jinja_block(token.text)
            if control_event is not None:
                event_kind, event_name = control_event
                if event_kind == "open":
                    control_stack.append(event_name)
                    saw_inner_control = True
                elif event_kind == "close":
                    _pop_matching_control(control_stack=control_stack, control_name=event_name)
                    if saw_branch_local_close and not control_stack:
                        return index
                    if (
                        not saw_branch_local_close
                        and html_depth == 1
                        and saw_inner_control
                        and not control_stack
                        and _should_close_unbalanced_flow(
                            tokens=tokens,
                            next_index=index + 1,
                            tag_name=tag_name,
                        )
                    ):
                        return index
            continue
        if token.kind != "html_tag" or token.tag_name != tag_name:
            continue
        if token.is_opening_tag and not token.is_self_closing_tag:
            if not saw_branch_local_close:
                html_depth += 1
            continue
        if not token.is_closing_tag:
            continue
        if html_depth > 1:
            html_depth -= 1
            continue
        if html_depth == 1:
            html_depth = 0
            if control_stack:
                saw_branch_local_close = True
            else:
                return index
    return None


def _classify_jinja_block(token_text: str) -> tuple[str, str] | None:
    inner = token_text[2:-2].strip()
    inner = inner.strip("-").strip()
    if not inner:
        return None

    keyword = inner.split(None, 1)[0]
    if keyword == "set":
        # Inline assignments should not affect control-depth tracking.
        if "=" in inner:
            return None
        return ("open", "set")
    if keyword in JINJA_CONTROL_OPENERS:
        return ("open", keyword)
    if keyword in JINJA_CONTROL_CLOSERS:
        return ("close", JINJA_CONTROL_CLOSERS[keyword])
    return None


def _pop_matching_control(*, control_stack: list[str], control_name: str) -> None:
    for index in range(len(control_stack) - 1, -1, -1):
        if control_stack[index] == control_name:
            del control_stack[index]
            return


def _should_close_unbalanced_flow(
    *, tokens: list[SourceToken], next_index: int, tag_name: str
) -> bool:
    for token in tokens[next_index:]:
        if token.kind == "jinja_comment":
            continue
        if token.kind == "text" and not token.text.strip():
            continue
        if token.kind == "text":
            return False
        if token.kind == "jinja_expr":
            return False
        if token.kind == "jinja_block":
            control_event = _classify_jinja_block(token.text)
            if control_event is None:
                continue
            event_kind, _ = control_event
            return event_kind == "close"
        if token.kind == "html_tag":
            if token.is_closing_tag and token.tag_name == tag_name:
                return False
            return True
    return True


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


def _extract_translatable_jinja_block_literals(block_body: str) -> list[str]:
    """Return user-facing literals from Jinja statements that feed rendered output."""

    inner = block_body.strip().strip("-").strip()
    if ".append(" not in inner:
        return []
    return _extract_translatable_jinja_literals(inner)


def _extract_translatable_jinja_literals(expr: str) -> list[str]:
    """Return user-facing string literals from a Jinja output expression."""

    literals: list[str] = []
    for match in JINJA_STRING_LITERAL_PATTERN.finditer(expr):
        if _is_subscript_literal(expr=expr, start=match.start(), end=match.end()):
            continue
        if _is_dict_key_literal(expr=expr, end=match.end()):
            continue
        try:
            value = ast.literal_eval(match.group("literal"))
        except (SyntaxError, ValueError):
            continue
        if isinstance(value, str) and _is_translatable_jinja_literal(value):
            literals.append(value.strip())
    return literals


def _is_subscript_literal(*, expr: str, start: int, end: int) -> bool:
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


def _is_dict_key_literal(*, expr: str, end: int) -> bool:
    next_index = end
    while next_index < len(expr) and expr[next_index].isspace():
        next_index += 1
    return next_index < len(expr) and expr[next_index] == ":"


def _is_translatable_jinja_literal(value: str) -> bool:
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


def _lex_source_tokens(source_text: str) -> list[SourceToken]:
    tokens: list[SourceToken] = []
    cursor = 0
    for match in TOKEN_PATTERN.finditer(source_text):
        if match.start() > cursor:
            tokens.append(
                SourceToken(
                    kind="text",
                    text=source_text[cursor : match.start()],
                    start=cursor,
                    end=match.start(),
                )
            )
        token = match.group(0)
        if token.startswith("{{"):
            tokens.append(
                SourceToken(
                    kind="jinja_expr",
                    text=token,
                    start=match.start(),
                    end=match.end(),
                )
            )
        elif token.startswith("{%"):
            tokens.append(
                SourceToken(
                    kind="jinja_block",
                    text=token,
                    start=match.start(),
                    end=match.end(),
                )
            )
        elif token.startswith("{#"):
            tokens.append(
                SourceToken(
                    kind="jinja_comment",
                    text=token,
                    start=match.start(),
                    end=match.end(),
                )
            )
        else:
            tokens.append(_build_html_tag_token(token=token, start=match.start(), end=match.end()))
        cursor = match.end()
    if cursor < len(source_text):
        tokens.append(
            SourceToken(
                kind="text",
                text=source_text[cursor:],
                start=cursor,
                end=len(source_text),
            )
        )
    if not tokens:
        return [SourceToken(kind="text", text="", start=0, end=0)]
    return tokens


def _build_html_tag_token(*, token: str, start: int, end: int) -> SourceToken:
    match = HTML_TAG_NAME_PATTERN.match(token)
    tag_name = match.group(1).lower() if match else None
    is_closing_tag = token.startswith("</")
    is_self_closing_tag = token.rstrip().endswith("/>") or tag_name in VOID_HTML_TAGS
    is_opening_tag = not is_closing_tag
    return SourceToken(
        kind="html_tag",
        text=token,
        start=start,
        end=end,
        tag_name=tag_name,
        is_opening_tag=is_opening_tag,
        is_closing_tag=is_closing_tag,
        is_self_closing_tag=is_self_closing_tag,
    )


def _rewrite_workspace_readme(*, source_dir: Path, output_dir: Path) -> None:
    source_readme = source_dir / "README.md"
    output_readme = output_dir / "README.md"
    upstream_readme = output_dir / UPSTREAM_README_NAME
    if source_readme.is_file():
        upstream_readme.write_text(source_readme.read_text(encoding="utf-8"), encoding="utf-8")

    output_readme.write_text(
        "\n".join(
            [
                "# Translation Workspace",
                "",
                "This folder is the sentence-preserving workspace generated from the",
                "compact DSW template.",
                "",
                "- Edit `src/**/*.j2` in place.",
                "- Generated `__tr_block_####` comment markers keep whole headings,",
                "  paragraphs, and list items together so later string extraction can work",
                "  on complete units without changing Jinja scope.",
                "- The older `src/_segments/...` split-file layout is obsolete and should not",
                "  exist in this workspace anymore.",
                "- Run `make compact-template` to rebuild a DSW-uploadable template.",
                "- Do not edit `.transform/manifest.json` manually.",
                "",
                f"The original upstream README is preserved in `{UPSTREAM_README_NAME}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _validate_template_dir(source_dir: Path) -> None:
    template_json = source_dir / "template.json"
    if not template_json.is_file():
        raise TemplateTransformError(f"Missing template.json in {source_dir}")
