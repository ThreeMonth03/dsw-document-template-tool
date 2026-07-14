"""Semantic version helpers shared by policy, paths, and runtime selection."""

from __future__ import annotations

from collections.abc import Iterable

from .errors import TranslationRepositoryError


def sorted_versions(versions: Iterable[str]) -> list[str]:
    """Sort version tags using numeric semantic version ordering."""

    return sorted(versions, key=version_sort_key)


def version_sort_key(version: str) -> tuple[int, ...]:
    """Return a sortable key for version tags such as ``v1.30.1``."""

    version_number = version_to_number(version)
    parts = version_number.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        raise TranslationRepositoryError(f"Expected numeric version tag, got {version!r}")
    return tuple(int(part) for part in parts)


def version_to_number(version: str) -> str:
    """Convert ``v1.30.1`` to ``1.30.1``."""

    if not version.startswith("v") or len(version) == 1:
        raise TranslationRepositoryError(f"Expected a version tag like v1.30.1, got {version!r}")
    return version[1:]


def version_matches_range(version: str, expression: str) -> bool:
    """Return whether ``version`` satisfies a simple semver range expression."""

    version_key = version_sort_key(version)
    terms = expression.split()
    if not terms:
        raise TranslationRepositoryError("Version policy match expression must not be empty")
    return all(_version_matches_range_term(version_key, term) for term in terms)


def _version_matches_range_term(version_key: tuple[int, ...], term: str) -> bool:
    for operator in (">=", "<=", ">", "<", "=="):
        if term.startswith(operator):
            expected = version_sort_key(term[len(operator) :])
            return _compare_version_key(version_key, operator, expected)
    if term.endswith("+"):
        expected = version_sort_key(term[:-1])
        return version_key >= expected
    return version_key == version_sort_key(term)


def _compare_version_key(
    version_key: tuple[int, ...],
    operator: str,
    expected: tuple[int, ...],
) -> bool:
    comparisons = {
        ">=": version_key >= expected,
        "<=": version_key <= expected,
        ">": version_key > expected,
        "<": version_key < expected,
        "==": version_key == expected,
    }
    try:
        return comparisons[operator]
    except KeyError as exc:
        raise TranslationRepositoryError(
            f"Unsupported version range operator {operator!r}"
        ) from exc
