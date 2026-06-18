#!/usr/bin/env python3
"""Filter semantic version tags from stdin by a minimum tag."""

from __future__ import annotations

import argparse
import re
import sys

VERSION_TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def parse_version_tag(tag: str) -> tuple[int, int, int] | None:
    """Return the numeric version tuple for a tag such as v1.30.0."""

    match = VERSION_TAG_PATTERN.match(tag)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def main() -> None:
    """Read tags from stdin and write sorted tags greater than or equal to min_tag."""

    parser = argparse.ArgumentParser()
    parser.add_argument("min_tag", help="Minimum semantic version tag, e.g. v1.30.0")
    args = parser.parse_args()

    min_version = parse_version_tag(args.min_tag)
    if min_version is None:
        raise SystemExit(f"Invalid minimum version tag: {args.min_tag}")

    tags = [tag.strip() for tag in sys.stdin if tag.strip()]
    supported_tags = [
        tag
        for tag in sorted(tags, key=lambda tag: parse_version_tag(tag) or (-1, -1, -1))
        if (version := parse_version_tag(tag)) is not None and version >= min_version
    ]
    print(" ".join(supported_tags))


if __name__ == "__main__":
    main()
