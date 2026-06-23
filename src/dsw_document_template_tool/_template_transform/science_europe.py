"""Science Europe-specific reversible source rewrites."""

from __future__ import annotations

from .science_europe_rules import (
    rewrite_science_europe_balanced_source_fragments,
    rewrite_science_europe_unbalanced_html_fragments,
)

__all__ = [
    "rewrite_science_europe_balanced_source_fragments",
    "rewrite_science_europe_unbalanced_html_fragments",
]
