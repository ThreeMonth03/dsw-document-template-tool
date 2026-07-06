"""HTML normalization and diff helpers used by regression checks."""

from __future__ import annotations

import difflib
import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

PRESERVE_WHITESPACE_TAGS = {"code", "pre", "script", "style"}


def normalize_html(html: str, *, ignore_patterns: list[str] | None = None) -> str:
    """Normalize rendered HTML so meaningful regressions diff cleanly."""

    soup = BeautifulSoup(html, "html.parser")
    _sort_tag_attributes(soup)
    _collapse_text_nodes(soup)

    normalized = soup.decode(formatter="minimal")
    normalized = re.sub(r">\s+<", "><", normalized)
    normalized = normalized.strip()
    return _remove_ignored_patterns(normalized, ignore_patterns or [])


def _sort_tag_attributes(soup: BeautifulSoup) -> None:
    """Sort attributes so equivalent HTML serializes consistently."""

    for tag in soup.find_all(True):
        if isinstance(tag, Tag):
            tag.attrs = {
                key: _stringify_attribute_value(tag.attrs[key]) for key in sorted(tag.attrs)
            }


def _stringify_attribute_value(value: object) -> str | list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return str(value)


def _collapse_text_nodes(soup: BeautifulSoup) -> None:
    """Collapse non-preformatted text nodes."""

    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString):
            continue
        parent_name = node.parent.name if node.parent is not None else None
        if parent_name in PRESERVE_WHITESPACE_TAGS:
            continue
        collapsed = re.sub(r"\s+", " ", str(node)).strip()
        node.replace_with(collapsed)


def _remove_ignored_patterns(normalized: str, ignore_patterns: list[str]) -> str:
    for pattern in ignore_patterns:
        normalized = re.sub(pattern, "", normalized, flags=re.MULTILINE)
    return normalized


def build_unified_diff(
    baseline_text: str,
    candidate_text: str,
    *,
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
) -> str:
    """Build a unified diff string for normalized HTML."""

    diff_lines = difflib.unified_diff(
        baseline_text.splitlines(),
        candidate_text.splitlines(),
        fromfile=baseline_label,
        tofile=candidate_label,
        lineterm="",
    )
    return "\n".join(diff_lines)
