"""Reversible expansion helpers for translation-friendly DSW templates."""

from __future__ import annotations

import ast
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
MANIFEST_PATH = Path(".transform") / "manifest.json"
MANIFEST_VERSION = 2
UPSTREAM_README_NAME = "UPSTREAM-README.md"
GENERATED_BLOCK_PREFIX = "__tr_block_"
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

    manifest = {
        "version": MANIFEST_VERSION,
        "format": "sentence_comment_markers",
        "files": transformed_files,
        "workspace_readme": "README.md",
        "upstream_readme": UPSTREAM_README_NAME if (source_dir / "README.md").is_file() else None,
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
        compacted_text = GENERATED_BLOCK_PATTERN.sub(
            lambda match: generated_block_body(match),
            source_path.read_text(encoding="utf-8"),
        )
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


def _expand_template_text(*, source_text: str) -> str:
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
                        and _should_close_unbalanced_flow(tokens=tokens, next_index=index + 1)
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


def _should_close_unbalanced_flow(*, tokens: list[SourceToken], next_index: int) -> bool:
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
