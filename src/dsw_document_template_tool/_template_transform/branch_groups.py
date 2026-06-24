"""Parse top-level Jinja branch groups for sentence rewrites."""

from __future__ import annotations

from dataclasses import dataclass

from .jinja_blocks import jinja_block_inner, jinja_block_keyword
from .scanner import SourceToken


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


def collect_top_level_branch_rewrite_groups(
    *, tokens: list[SourceToken]
) -> list[BranchRewriteGroup]:
    """Collect top-level if/elif/else groups with at least one alternative."""

    return _collect_top_level_rewrite_groups(tokens=tokens, require_alternatives=True)


def collect_top_level_optional_rewrite_groups(
    *, tokens: list[SourceToken]
) -> list[BranchRewriteGroup]:
    """Collect top-level optional if groups, including single-branch groups."""

    return _collect_top_level_rewrite_groups(tokens=tokens, require_alternatives=False)


def active_jinja_if_conditions_at(*, tokens: list[SourceToken], token_index: int) -> list[str]:
    """Return the active surrounding Jinja if/elif conditions before one token."""

    conditions: list[str] = []
    for token in tokens[:token_index]:
        if token.kind != "jinja_block":
            continue
        inner = jinja_block_inner(token.text)
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


def _collect_top_level_rewrite_groups(
    *, tokens: list[SourceToken], require_alternatives: bool
) -> list[BranchRewriteGroup]:
    groups: list[BranchRewriteGroup] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "jinja_block" and jinja_block_keyword(token.text) == "if":
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
        keyword = jinja_block_keyword(token.text)
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
