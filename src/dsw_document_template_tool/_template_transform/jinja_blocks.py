"""Small helpers for reading Jinja block tokens."""

from __future__ import annotations


def jinja_block_inner(token_text: str) -> str:
    """Return the normalized body inside one `{% ... %}` token."""

    return token_text[2:-2].strip().strip("-").strip()


def jinja_block_keyword(token_text: str) -> str:
    """Return the first keyword from one `{% ... %}` token body."""

    inner = jinja_block_inner(token_text)
    return inner.split(None, 1)[0] if inner else ""


def jinja_block_trims_following_whitespace(token_text: str) -> bool:
    """Return whether one Jinja block trims following whitespace."""

    return token_text.rstrip().endswith("-%}")


def jinja_block_trims_previous_whitespace(token_text: str) -> bool:
    """Return whether one Jinja block trims preceding whitespace."""

    return token_text.startswith("{%-")
