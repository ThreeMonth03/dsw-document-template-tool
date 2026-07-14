"""Science Europe-specific reversible source rewrites."""

from __future__ import annotations

from .profile import TemplateIdentity, TransformContext, TransformTrace
from .science_europe_balanced_rules import (
    rewrite_science_europe_balanced_source_fragments,
)
from .science_europe_unbalanced_rules import (
    rewrite_science_europe_unbalanced_html_fragments,
)

PROFILE_ID = "science-europe"

__all__ = [
    "PROFILE_ID",
    "is_science_europe_template",
    "rewrite_science_europe_source",
    "rewrite_science_europe_balanced_source_fragments",
    "rewrite_science_europe_unbalanced_html_fragments",
]


def is_science_europe_template(identity: TemplateIdentity) -> bool:
    """Return whether the local profile owns this template."""

    return identity.organization_id == "dsw" and identity.template_id == "science-europe"


def rewrite_science_europe_source(
    source_text: str,
    *,
    context: TransformContext,
    trace: TransformTrace,
    phase: str,
) -> str:
    """Apply the named Science Europe rewrite phase with trace metadata."""

    if phase == "balanced":
        return rewrite_science_europe_balanced_source_fragments(
            source_text,
            source_file=context.relative_path,
            trace=trace,
        )
    if phase == "unbalanced":
        return rewrite_science_europe_unbalanced_html_fragments(
            source_text,
            apply_localization_rewrites=context.apply_local_patches,
            source_file=context.relative_path,
            trace=trace,
        )
    raise ValueError(f"Unknown Science Europe rewrite phase: {phase}")
