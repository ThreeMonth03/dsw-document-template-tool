"""Small helpers for exact, reversible source rewrites."""

from __future__ import annotations

from dataclasses import dataclass

from .markers import encode_marker_payload
from .profile import TransformTrace

ReversibleReplacement = tuple[str, str]
ReversibleReplacements = tuple[ReversibleReplacement, ...]

__all__ = [
    "ReversibleReplacement",
    "ReversibleReplacementGroup",
    "ReversibleReplacements",
    "apply_reversible_replacement_groups",
    "apply_reversible_replacements",
    "wrap_reversible_branch_sentence_rewrite",
]


@dataclass(frozen=True)
class ReversibleReplacementGroup:
    """A named group of exact source rewrites.

    The group ID is intentionally diagnostic-only. It gives template-specific
    rewrite modules a place to document why a set of replacements exists without
    changing the generated template output.
    """

    group_id: str
    replacements: ReversibleReplacements
    rationale: str = ""


def apply_reversible_replacements(
    source_text: str,
    replacements: ReversibleReplacements,
) -> str:
    """Apply exact replacements and preserve the original text for compaction."""

    rewritten_text, _match_count = _apply_reversible_replacements(source_text, replacements)
    return rewritten_text


def _apply_reversible_replacements(
    source_text: str,
    replacements: ReversibleReplacements,
) -> tuple[str, int]:
    """Apply exact replacements and return the number of matched rules."""

    rewritten_text = source_text
    match_count = 0
    for original, replacement in replacements:
        if original not in rewritten_text:
            continue
        rewritten_text = rewritten_text.replace(
            original,
            wrap_reversible_branch_sentence_rewrite(
                original=original,
                replacement=replacement,
            ),
            1,
        )
        match_count += 1
    return rewritten_text, match_count


def apply_reversible_replacement_groups(
    source_text: str,
    groups: tuple[ReversibleReplacementGroup, ...],
    *,
    source_file: str = "",
    trace: TransformTrace | None = None,
) -> str:
    """Apply named exact replacement groups in order."""

    rewritten_text = source_text
    for group in groups:
        rewritten_text, match_count = _apply_reversible_replacements(
            rewritten_text,
            group.replacements,
        )
        if trace is not None:
            trace.record(
                group_id=group.group_id,
                rationale=group.rationale,
                source_file=source_file,
                match_count=match_count,
            )
    return rewritten_text


def wrap_reversible_branch_sentence_rewrite(*, original: str, replacement: str) -> str:
    """Wrap replacement text with a marker containing the exact original text."""

    encoded_original = encode_marker_payload(original)
    return (
        f"{{# __tr_branch_sentence_original:{encoded_original} #}}"
        f"{replacement}"
        "{# __tr_branch_sentence_original:end #}"
    )
