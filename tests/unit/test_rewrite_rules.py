"""Tests for reversible exact rewrite helpers."""

from __future__ import annotations

import base64

from dsw_document_template_tool._template_transform.branch_sentences import (
    restore_branch_sentence_rewrites,
)
from dsw_document_template_tool._template_transform.profile import TransformTrace
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


def test_reversible_replacement_groups_record_named_trace() -> None:
    """Applied group IDs should make generated workspaces traceable to code."""

    trace = TransformTrace(profile_id="test")
    rewritten_text = apply_reversible_replacement_groups(
        "alpha beta",
        (
            ReversibleReplacementGroup(
                "test.alpha",
                (("alpha", "translated alpha"),),
                "Keep the test sentence complete.",
            ),
        ),
        source_file="src/index.html.j2",
        trace=trace,
    )

    assert "translated alpha" in rewritten_text
    assert trace.to_manifest() == {
        "profile": "test",
        "applications": [
            {
                "group_id": "test.alpha",
                "rationale": "Keep the test sentence complete.",
                "source_file": "src/index.html.j2",
                "match_count": 1,
            }
        ],
    }


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

    assert [group.group_id for group in balanced_groups] == [
        "science-europe.balanced.conditions",
        "science-europe.balanced.governance",
        "science-europe.balanced.computer-readable",
        "science-europe.balanced.reuse",
        "science-europe.balanced.nonreuse",
        "science-europe.balanced.publication",
    ]
    assert [group.group_id for group in unbalanced_groups] == [
        "science-europe.unbalanced.structure",
        "science-europe.unbalanced.localization",
    ]
    assert sum(len(group.replacements) for group in balanced_groups) == 27
    assert sum(len(group.replacements) for group in unbalanced_groups) == 16
    assert all(group.rationale for group in (*balanced_groups, *unbalanced_groups))

    for group in (*balanced_groups, *unbalanced_groups):
        originals = [original for original, _replacement in group.replacements]
        assert all(original for original in originals)
        assert all(replacement for _original, replacement in group.replacements)
        assert len(originals) == len(set(originals))


def test_science_europe_pid_negative_sentence_is_conditional() -> None:
    """PID negative sentence should not render after a positive PID branch."""

    groups = _build_unbalanced_html_fragment_groups()
    original, replacement = next(
        pair
        for group in groups
        for pair in group.replacements
        if "unique and persistent identifiers will not be applied" in pair[0]
    )

    rewritten = apply_reversible_replacements(original, ((original, replacement),))

    assert "publishedDataIdentifierAUuid == uuids.publishedDataIdentifierYesAUuid" in rewritten
    assert "{%- else -%}" in rewritten
    assert (
        "{%- endfor -%}\n"
        "                        <p>Within this repository, unique and persistent "
        "identifiers will not be applied.</p>"
    ) not in rewritten


def test_science_europe_pid_negative_rewrite_is_local_patch() -> None:
    """Compact-vs-expanded regression should not include local behavior patches."""

    groups = _build_unbalanced_html_fragment_groups(apply_localization_rewrites=False)

    assert not any(
        "unique and persistent identifiers will not be applied" in original
        for group in groups
        for original, _replacement in group.replacements
    )
