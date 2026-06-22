"""Shared data models for translation tree workflows.

These models are intentionally free of HTML/Jinja scanner dependencies so they
can be reused by export, sync, audit, and future translation migration planning.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranslationUnit:
    """One translator-facing unit captured from an expanded wrapper block."""

    source_file: str
    wrapper_name: str
    wrapper_order: int
    wrapper_key: str
    wrapper_folder_name: str
    wrapper_source_hash: str
    unit_order: int
    unit_key: str
    unit_folder_name: str
    unit_source_hash: str
    unit_start: int
    unit_end: int
    source_text: str


@dataclass(frozen=True)
class OutlineUnit:
    """One rendered outline row for a translator-facing unit."""

    source_file: str
    wrapper_order: int
    wrapper_folder_name: str
    unit_folder_name: str
    document_path: Path
    sentence_text: str
    is_translated: bool


@dataclass(frozen=True)
class TranslationEntry:
    """Translator-edited text plus the document it came from."""

    text: str
    document_path: str


@dataclass(frozen=True)
class TranslationTreeAuditIssue:
    """One machine-checkable issue in a translator-facing tree."""

    code: str
    location: str
    message: str


class TranslationTreeError(RuntimeError):
    """Raised when the translator-facing tree is invalid."""
