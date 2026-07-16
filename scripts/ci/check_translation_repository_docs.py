#!/usr/bin/env python3
"""Check public translated-template repository docs cover required topics."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class TopicCheck:
    """One required public-repository documentation topic."""

    name: str
    patterns: tuple[str, ...]
    description: str


REQUIRED_TOPICS: tuple[TopicCheck, ...] = (
    TopicCheck(
        name="branch model",
        patterns=(r"\boperations\b", r"sync/v\*", r"release assets"),
        description="operations branch, sync/v* branches, and release assets",
    ),
    TopicCheck(
        name="manual DSW import",
        patterns=(r"manual(?:ly)?", r"\bDSW\b", r"\bimport\b"),
        description="manual DSW import policy",
    ),
    TopicCheck(
        name="workflow synchronization token",
        patterns=(r"TRANSLATION_AUTOMATION_TOKEN", r"workflow scope|Workflows:", r"gh secret set"),
        description="TRANSLATION_AUTOMATION_TOKEN setup with workflow permission",
    ),
    TopicCheck(
        name="version policy snippets",
        patterns=(
            r"state:\s*available",
            r"state:\s*active",
            r"state:\s*maintenance",
            r"state:\s*published",
            r"state:\s*archived",
            r"publish_release:\s*true",
            r"publish_release:\s*false",
        ),
        description=(
            "copy-ready available/active/maintenance/published/archived version_policy examples"
        ),
    ),
    TopicCheck(
        name="version policy precedence",
        patterns=(r"matching rules", r"file order", r"explicitly"),
        description="defaults/rules/overrides precedence and partial-layer behavior",
    ),
    TopicCheck(
        name="tooling bootstrap contract",
        patterns=(r"tooling\.repository", r"tooling\.ref", r"one-line", r"duplicate-key"),
        description="one-line tooling checkout fields followed by strict config validation",
    ),
)

FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"translation/v\*", "retired translation/v* branch model"),
    (
        r"DOCUMENT_TEMPLATE_PUBLISH_TOKEN[^.\n]*(must be set|required for publishing)",
        "retired document-template publish token requirement",
    ),
)
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^]]+\]\((?P<target>[^)]+)\)")


def main() -> None:
    """Run the public-repository documentation coverage check."""

    parser = argparse.ArgumentParser(
        description="check public translated-template repository docs cover required topics",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="Path to the public translated-template repository checkout.",
    )
    args = parser.parse_args()

    try:
        report = check_repository(args.repo)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if report.failures:
        print(report.render(), file=sys.stderr)
        raise SystemExit(1)

    print(report.render())


@dataclass(frozen=True)
class CheckReport:
    """Rendered public-repository documentation check result."""

    repo: Path
    checked_files: tuple[Path, ...]
    failures: tuple[str, ...]

    def render(self) -> str:
        """Render a human-readable report."""

        lines = [
            f"Repository: {self.repo}",
            f"Checked Markdown files: {len(self.checked_files)}",
        ]
        if self.failures:
            lines.append("Missing or stale documentation topics:")
            lines.extend(f"- {failure}" for failure in self.failures)
        else:
            lines.append("SUCCESS: Public repository docs cover required operations topics.")
        return "\n".join(lines)


def check_repository(repo: Path) -> CheckReport:
    """Return a coverage report for a public translated-template repository."""

    repo = repo.resolve()
    if not repo.is_dir():
        raise OSError(f"Repository does not exist: {repo}")

    markdown_files = tuple(sorted(_iter_markdown_files(repo)))
    if not markdown_files:
        return CheckReport(
            repo=repo,
            checked_files=(),
            failures=("No Markdown files found in README.md or docs/.",),
        )

    docs_text = "\n\n".join(path.read_text(encoding="utf-8") for path in markdown_files)
    failures: list[str] = []

    for topic in REQUIRED_TOPICS:
        missing_patterns = [
            pattern
            for pattern in topic.patterns
            if re.search(pattern, docs_text, flags=re.I) is None
        ]
        if missing_patterns:
            failures.append(
                f"{topic.name}: expected {topic.description}; missing patterns "
                + ", ".join(f"`{pattern}`" for pattern in missing_patterns)
            )

    for pattern, label in FORBIDDEN_PATTERNS:
        if re.search(pattern, docs_text, flags=re.I | re.S):
            failures.append(f"{label}: matched forbidden pattern `{pattern}`")

    failures.extend(_missing_relative_link_failures(repo, markdown_files))

    return CheckReport(
        repo=repo,
        checked_files=markdown_files,
        failures=tuple(failures),
    )


def _iter_markdown_files(repo: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    readme = repo / "README.md"
    if readme.is_file():
        candidates.append(readme)
    docs_dir = repo / "docs"
    if docs_dir.is_dir():
        candidates.extend(path for path in docs_dir.rglob("*.md") if "_build" not in path.parts)
    glossary_dir = repo / "glossary"
    if glossary_dir.is_dir():
        candidates.extend(glossary_dir.rglob("*.md"))
    return tuple(candidates)


def _missing_relative_link_failures(
    repo: Path,
    markdown_files: tuple[Path, ...],
) -> tuple[str, ...]:
    """Return failures for local Markdown links whose targets do not exist."""

    failures: list[str] = []
    for document in markdown_files:
        markdown = document.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_PATTERN.finditer(markdown):
            target = match.group("target").strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target_path = (document.parent / unquote(parsed.path)).resolve()
            if not target_path.exists():
                failures.append(
                    f"broken relative link: {document.relative_to(repo)} links to `{target}`"
                )
    return tuple(failures)


if __name__ == "__main__":
    main()
