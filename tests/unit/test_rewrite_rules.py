"""Tests for reversible exact rewrite helpers."""

from __future__ import annotations

import base64

from dsw_document_template_tool._template_transform.branch_sentences import (
    restore_branch_sentence_rewrites,
)
from dsw_document_template_tool._template_transform.rewrite_rules import (
    ReversibleReplacementGroup,
    apply_reversible_replacement_groups,
    apply_reversible_replacements,
)
from dsw_document_template_tool._template_transform.science_europe_balanced_rules import (
    _build_balanced_source_fragment_groups,
)
from dsw_document_template_tool._template_transform.science_europe_unbalanced_rules import (
    _build_unbalanced_html_fragment_groups,
)


def test_reversible_replacement_wraps_original_source_for_compaction() -> None:
    source_text = "<p>Hello fragmented world.</p>"

    rewritten_text = apply_reversible_replacements(
        source_text,
        (("fragmented", "translation-friendly"),),
    )

    encoded_original = base64.urlsafe_b64encode(b"fragmented").decode("ascii")
    assert f"__tr_branch_sentence_original:{encoded_original}" in rewritten_text
    assert "translation-friendly" in rewritten_text
    assert "fragmented" not in rewritten_text


def test_reversible_replacement_groups_apply_in_order() -> None:
    source_text = "alpha beta gamma"

    rewritten_text = apply_reversible_replacement_groups(
        source_text,
        (
            ReversibleReplacementGroup("first", (("alpha", "beta"),)),
            ReversibleReplacementGroup("second", (("gamma", "delta"),)),
        ),
    )

    assert "first" not in rewritten_text
    assert "second" not in rewritten_text
    assert "beta" in rewritten_text
    assert "delta" in rewritten_text


def test_branch_sentence_restore_ignores_end_marker_as_payload() -> None:
    """Adjacent reversible markers should not treat the end marker as a new start."""

    rewritten_text = apply_reversible_replacements(
        "alpha beta",
        (
            ("alpha", "translated alpha"),
            ("beta", "translated beta"),
        ),
    )

    assert restore_branch_sentence_rewrites(rewritten_text) == "alpha beta"


def test_branch_sentence_restore_handles_nested_markers() -> None:
    """Nested reversible markers should compact back from the inside out."""

    inner = apply_reversible_replacements("beta", (("beta", "translated beta"),))
    outer = apply_reversible_replacements(
        f"alpha {inner}",
        ((f"alpha {inner}", "translated alpha beta"),),
    )

    assert restore_branch_sentence_rewrites(outer) == "alpha beta"


def test_science_europe_rewrite_groups_keep_expected_rule_sets() -> None:
    """Science Europe exact rewrites should stay grouped and non-duplicated."""

    balanced_groups = _build_balanced_source_fragment_groups()
    unbalanced_groups = _build_unbalanced_html_fragment_groups()

    assert [group.name for group in balanced_groups] == ["balanced_science_europe_sentence_blocks"]
    assert [group.name for group in unbalanced_groups] == [
        "unbalanced_science_europe_html_fragments"
    ]
    assert len(balanced_groups[0].replacements) == 26
    assert len(unbalanced_groups[0].replacements) == 14

    for group in (*balanced_groups, *unbalanced_groups):
        originals = [original for original, _replacement in group.replacements]
        assert all(original for original in originals)
        assert all(replacement for _original, replacement in group.replacements)
        assert len(originals) == len(set(originals))
