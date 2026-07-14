"""Named source-quality guards learned from supported upstream templates.

These rules do not change executable template source. They improve translator-facing
sentence previews and make parser regressions fail loudly. Keep each upstream-specific
addition named and documented so maintainers can trace why it exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFragmentRule:
    """Sentence shapes that indicate an incorrectly split translation unit."""

    rule_id: str
    rationale: str
    exact_sentences: frozenset[str] = frozenset()
    prefixes: tuple[str, ...] = ()

    def matches(self, sentence: str) -> bool:
        normalized = sentence.lower()
        return normalized in self.exact_sentences or normalized.startswith(self.prefixes)


@dataclass(frozen=True)
class SentenceRepairRule:
    """Display-only repair for words joined by upstream Jinja boundaries."""

    rule_id: str
    rationale: str
    pattern: re.Pattern[str]
    replacement: str


SOURCE_FRAGMENT_RULES = (
    SourceFragmentRule(
        rule_id="science-europe.fragmented-branch-clause",
        rationale=(
            "Science Europe conditional clauses must stay with their surrounding sentence; "
            "these remnants indicate that expand/export split a branch at the wrong boundary."
        ),
        exact_sentences=frozenset(
            {
                "available via:",
                "available with",
                "this data.",
                "this data are",
                "we will use.",
            }
        ),
        prefixes=(
            '" of this dataset',
            ", but decided ",
            ", legally",
            ", which",
            "and we will ",
            "but we won't ",
            'in order to "',
        ),
    ),
)

SENTENCE_REPAIR_RULES = tuple(
    SentenceRepairRule(
        rule_id=f"science-europe.joined-word.{joined}",
        rationale=(
            "Restore a space or upstream spelling in translator-facing text when Jinja "
            "concatenation hides the intended sentence boundary."
        ),
        pattern=re.compile(rf"\b{joined}\b", re.IGNORECASE),
        replacement=replacement,
    )
    for joined, replacement in (
        ("becauseit", "because it"),
        ("legaly", "legally"),
        ("dataare", "data are"),
        ("datamay", "data may"),
        ("usethe", "use the"),
        ("useonly", "use only"),
        ("withfollowing", "with following"),
    )
)


def matching_source_fragment_rule(sentence: str) -> SourceFragmentRule | None:
    """Return the first named rule matched by a translator-facing sentence."""

    return next((rule for rule in SOURCE_FRAGMENT_RULES if rule.matches(sentence)), None)


def repair_sentence_text(sentence: str) -> str:
    """Apply display-only sentence repairs without mutating template source."""

    repaired = sentence
    for rule in SENTENCE_REPAIR_RULES:
        repaired = rule.pattern.sub(rule.replacement, repaired)
    return repaired
