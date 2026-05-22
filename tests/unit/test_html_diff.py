"""Tests for HTML normalization and diff rendering."""

from __future__ import annotations

from dsw_document_template_tool.html_diff import build_unified_diff, normalize_html


def test_normalize_html_collapses_whitespace_and_attribute_order() -> None:
    """Equivalent HTML should normalize to the same canonical output."""

    left = '<div class="hero" id="a">  Hello   <span data-x="1" data-a="2"> world </span></div>'
    right = '<div id="a" class="hero">Hello<span data-a="2" data-x="1">world</span></div>'

    assert normalize_html(left) == normalize_html(right)


def test_normalize_html_applies_ignore_patterns() -> None:
    """Configured ignore patterns should scrub known dynamic fragments."""

    html = "<p>Generated at: 2026-05-21 10:00:00</p>"
    normalized = normalize_html(html, ignore_patterns=[r"Generated at: .*"])

    assert "Generated at:" not in normalized


def test_build_unified_diff_marks_changes() -> None:
    """Diff output should mention both labels and the changed lines."""

    diff = build_unified_diff(
        "alpha\nbeta",
        "alpha\ngamma",
        baseline_label="old",
        candidate_label="new",
    )

    assert "--- old" in diff
    assert "+++ new" in diff
    assert "-beta" in diff
    assert "+gamma" in diff
