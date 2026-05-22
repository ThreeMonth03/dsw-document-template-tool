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

    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        ordered_attrs: dict[str, str | list[str]] = {}
        for key in sorted(tag.attrs):
            value = tag.attrs[key]
            if isinstance(value, list):
                ordered_attrs[key] = [str(item) for item in value]
            else:
                ordered_attrs[key] = str(value)
        tag.attrs = ordered_attrs

    for node in list(soup.find_all(string=True)):
        if not isinstance(node, NavigableString):
            continue
        parent_name = node.parent.name if node.parent is not None else None
        if parent_name in PRESERVE_WHITESPACE_TAGS:
            continue
        collapsed = re.sub(r"\s+", " ", str(node)).strip()
        node.replace_with(collapsed)

    normalized = soup.decode(formatter="minimal")
    normalized = re.sub(r">\s+<", "><", normalized)
    normalized = normalized.strip()

    for pattern in ignore_patterns or []:
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
