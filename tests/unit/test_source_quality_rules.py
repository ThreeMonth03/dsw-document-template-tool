"""Tests for named translator-facing source-quality rules."""

from dsw_document_template_tool._translation_tree.source_quality_rules import (
    matching_source_fragment_rule,
    repair_sentence_text,
)


def test_science_europe_fragment_rule_is_named_and_traceable() -> None:
    """A known broken branch clause should identify the rule that caught it."""

    rule = matching_source_fragment_rule("and we will make this available.")

    assert rule is not None
    assert rule.rule_id == "science-europe.fragmented-branch-clause"
    assert rule.rationale


def test_sentence_repair_is_display_only_and_deterministic() -> None:
    """Known joined words should be legible in translator-facing sentence previews."""

    assert repair_sentence_text("becauseit is legaly available") == (
        "because it is legally available"
    )
