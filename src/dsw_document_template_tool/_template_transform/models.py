"""Shared models for template transform helpers."""

from __future__ import annotations


class TemplateTransformError(RuntimeError):
    """Raised when a template cannot be expanded or compacted safely."""
