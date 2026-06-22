"""Low-level HTML/Jinja tokenization helpers for template transforms."""

from __future__ import annotations

import re
from dataclasses import dataclass

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


def lex_source_tokens(source_text: str) -> list[SourceToken]:
    """Tokenize one Jinja/HTML source string while preserving offsets."""

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


def find_matching_tag_end(*, tokens: list[SourceToken], start_index: int) -> int | None:
    """Find the matching close token for one opening HTML token."""

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
