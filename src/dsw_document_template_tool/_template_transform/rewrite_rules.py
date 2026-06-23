"""Small helpers for exact, reversible source rewrites."""

from __future__ import annotations

from dataclasses import dataclass

from .markers import encode_marker_payload

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

    The group name is intentionally diagnostic-only. It gives template-specific
    rewrite modules a place to document why a set of replacements exists without
    changing the generated template output.
    """

    name: str
    replacements: ReversibleReplacements


def apply_reversible_replacements(
    source_text: str,
    replacements: ReversibleReplacements,
) -> str:
    """Apply exact replacements and preserve the original text for compaction."""

    rewritten_text = source_text
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
    return rewritten_text


def apply_reversible_replacement_groups(
    source_text: str,
    groups: tuple[ReversibleReplacementGroup, ...],
) -> str:
    """Apply named exact replacement groups in order."""

    rewritten_text = source_text
    for group in groups:
        rewritten_text = apply_reversible_replacements(
            rewritten_text,
            group.replacements,
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
