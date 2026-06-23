"""Tests for reversible exact rewrite helpers."""

from __future__ import annotations

import base64

from dsw_document_template_tool._template_transform.rewrite_rules import (
    ReversibleReplacementGroup,
    apply_reversible_replacement_groups,
    apply_reversible_replacements,
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
