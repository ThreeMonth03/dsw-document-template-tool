"""Strict scalar and mapping readers shared by repository config loaders."""

from __future__ import annotations

from .errors import TranslationRepositoryError


def required_str(payload: object, key: str) -> str:
    """Read one required non-empty string."""

    if not isinstance(payload, dict):
        raise TranslationRepositoryError(f"Expected mapping while reading {key!r}")
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise TranslationRepositoryError(f"Expected non-empty string at {key!r}")
    return value


def required_str_list(payload: object, key: str) -> list[str]:
    """Read one required list of non-empty strings."""

    if not isinstance(payload, dict):
        raise TranslationRepositoryError(f"Expected mapping while reading {key!r}")
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise TranslationRepositoryError(f"Expected non-empty string list at {key!r}")
    return value


def optional_bool(payload: object, key: str, *, default: bool) -> bool:
    """Read one optional strict boolean."""

    if not isinstance(payload, dict):
        raise TranslationRepositoryError(f"Expected mapping while reading {key!r}")
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise TranslationRepositoryError(f"Expected boolean at {key!r}")
    return value


def optional_str(payload: object, key: str, *, default: str | None = "") -> str | None:
    """Read one optional string while preserving an explicit nullable default."""

    if not isinstance(payload, dict):
        raise TranslationRepositoryError(f"Expected mapping while reading {key!r}")
    value = payload.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise TranslationRepositoryError(f"Expected string at {key!r}")
    return value


def reject_unknown_keys(payload: object, allowed: set[str], section: str) -> None:
    """Reject misspelled or retired configuration fields."""

    if not isinstance(payload, dict):
        raise TranslationRepositoryError(f"{section} must be a mapping")
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise TranslationRepositoryError(f"Unknown {section} field(s): {', '.join(unknown)}")
