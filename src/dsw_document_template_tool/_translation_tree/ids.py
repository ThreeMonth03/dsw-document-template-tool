"""Stable identifiers and hashing helpers for translation-tree records."""

from __future__ import annotations

import hashlib


def hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()
