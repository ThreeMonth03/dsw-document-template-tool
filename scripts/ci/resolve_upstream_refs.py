#!/usr/bin/env python3
"""Resolve upstream template refs, including semantic-version ranges."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

VERSION_TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
GITHUB_OWNER_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_version_tag(tag: str) -> tuple[int, int, int] | None:
    """Return the numeric version tuple for a tag such as v1.30.0."""

    match = VERSION_TAG_PATTERN.match(tag)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def list_remote_version_tags(remote: str) -> list[str]:
    """Return upstream semantic-version tags sorted by version."""

    result = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", normalize_git_remote(remote), "v*"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    tags: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        ref = line.split()[1]
        tag = ref.removeprefix("refs/tags/")
        if parse_version_tag(tag) is not None:
            tags.append(tag)
    return sorted(tags, key=lambda tag: parse_version_tag(tag) or (-1, -1, -1))


def normalize_git_remote(remote: str) -> str:
    """Return a git remote URL, accepting GitHub owner/repo shorthand."""

    remote = remote.strip()
    if Path(remote).exists():
        return remote
    if remote.startswith(("/", ".", "~", "git@")) or "://" in remote:
        return remote
    if GITHUB_OWNER_REPO_PATTERN.fullmatch(remote):
        return f"https://github.com/{remote}.git"
    return remote


def dedupe_preserving_order(items: Iterable[str]) -> list[str]:
    """Return items without duplicates while preserving the first occurrence."""

    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def resolve_refs(remote: str, refs: Iterable[str]) -> list[str]:
    """Resolve refs, expanding inputs like v1.29.1+ into matching version tags."""

    remote_tags: list[str] | None = None
    resolved_refs: list[str] = []
    for ref in refs:
        if ref.endswith("+"):
            min_tag = ref[:-1]
            min_version = parse_version_tag(min_tag)
            if min_version is None:
                raise ValueError(f"Invalid version range ref: {ref}")
            if remote_tags is None:
                remote_tags = list_remote_version_tags(remote)
            resolved_refs.extend(
                tag
                for tag in remote_tags
                if (version := parse_version_tag(tag)) is not None and version >= min_version
            )
        else:
            resolved_refs.append(ref)
    return dedupe_preserving_order(resolved_refs)


def main() -> None:
    """Resolve refs and print them as a shell-friendly space-separated list."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", required=True, help="Git remote URL or GitHub owner/name.")
    parser.add_argument("refs", nargs="+", help="Refs to resolve, e.g. latest main v1.29.1+")
    args = parser.parse_args()

    try:
        print(" ".join(resolve_refs(remote=args.remote, refs=args.refs)))
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
