"""Parser and renderer for translator-editable ``translation.md`` files."""

from __future__ import annotations

import re
from pathlib import Path

from .models import TranslationTreeError, TranslationUnit

SOURCE_FENCE = "~~~jinja"
TRANSLATION_DOC_NAME = "translation.md"
TRANSLATION_SECTION_PATTERN = re.compile(
    r"### Translation \((?P<target_lang>[^)]+)\)\n\n~~~jinja\n"
    r"(?P<translation_text>.*?)\n~~~(?:\n|\Z)",
    re.DOTALL,
)
SENTENCE_SECTION_PATTERN = re.compile(
    r"### Sentence \((?P<source_lang>[^)]+)\)\n\n```text\n"
    r"(?P<sentence_text>.*?)\n```",
    re.DOTALL,
)


def render_translation_document(
    *,
    unit: TranslationUnit,
    source_lang: str,
    target_lang: str,
    sentence_text: str,
    translation_text: str,
) -> str:
    """Render one translator-facing Markdown document."""

    return "\n".join(
        [
            "# Translation Unit",
            "",
            f"Edit only the `Translation ({target_lang})` block. Keep every placeholder",
            "shown in the source sentence, such as `{name}`, but reorder placeholders",
            "when the target language needs it.",
            "",
            f"### Sentence ({source_lang})",
            "",
            "```text",
            sentence_text,
            "```",
            "",
            f"### Translation ({target_lang})",
            "",
            SOURCE_FENCE,
            translation_text,
            "~~~",
            "",
            "<details>",
            "<summary>Machine metadata</summary>",
            "",
            f"- Source File: `{unit.source_file}`",
            f"- Wrapper Name: `{unit.wrapper_name}`",
            f"- Wrapper Order: `{unit.wrapper_order}`",
            f"- Wrapper Key: `{unit.wrapper_key}`",
            f"- Unit Key: `{unit.unit_key}`",
            f"- Source Hash: `{unit.unit_source_hash}`",
            "",
            "Do not edit this section manually.",
            "",
            "</details>",
            "",
        ]
    )


def parse_translation_document(
    *,
    document_path: Path,
    source_lang: str,
    target_lang: str,
) -> str:
    """Read the translation block from one translator-facing Markdown file."""

    return parse_translation_markdown(
        markdown_text=document_path.read_text(encoding="utf-8"),
        location=str(document_path),
        source_lang=source_lang,
        target_lang=target_lang,
    )


def parse_translation_markdown(
    *,
    markdown_text: str,
    location: str,
    source_lang: str,
    target_lang: str,
) -> str:
    """Read the translation block from in-memory translation Markdown."""

    sentence_match = SENTENCE_SECTION_PATTERN.search(markdown_text)
    translation_match = TRANSLATION_SECTION_PATTERN.search(markdown_text)
    if sentence_match is None or translation_match is None:
        raise TranslationTreeError(f"Invalid translation document at {location}")
    if (
        sentence_match.group("source_lang") != source_lang
        or translation_match.group("target_lang") != target_lang
    ):
        raise TranslationTreeError(
            "Unexpected language headings in translation document at "
            f"{location}: expected {source_lang}/{target_lang}"
        )
    return translation_match.group("translation_text")


def parse_sentence_text(*, document_path: Path, source_lang: str) -> str:
    """Read the plain source sentence from one translator-facing Markdown file."""

    return parse_sentence_markdown(
        markdown_text=document_path.read_text(encoding="utf-8"),
        location=str(document_path),
        source_lang=source_lang,
    )


def parse_sentence_markdown(
    *,
    markdown_text: str,
    location: str,
    source_lang: str,
) -> str:
    """Read the source sentence from in-memory translation Markdown."""

    sentence_match = SENTENCE_SECTION_PATTERN.search(markdown_text)
    if sentence_match is None:
        raise TranslationTreeError(f"Invalid translation document at {location}")
    if sentence_match.group("source_lang") != source_lang:
        raise TranslationTreeError(
            "Unexpected source language heading in translation document at "
            f"{location}: expected {source_lang}"
        )
    return sentence_match.group("sentence_text")


def replace_translation_text(
    *,
    document_path: Path,
    target_lang: str,
    translation_text: str,
) -> None:
    """Replace only the editable translation block in a translation document."""

    markdown_text = document_path.read_text(encoding="utf-8")
    match = TRANSLATION_SECTION_PATTERN.search(markdown_text)
    if match is None:
        raise TranslationTreeError(f"Invalid translation document at {document_path}")
    if match.group("target_lang") != target_lang:
        raise TranslationTreeError(
            "Unexpected target language heading in translation document at "
            f"{document_path}: expected {target_lang}"
        )
    replacement = f"### Translation ({target_lang})\n\n{SOURCE_FENCE}\n{translation_text}\n~~~\n"
    document_path.write_text(
        markdown_text[: match.start()] + replacement + markdown_text[match.end() :],
        encoding="utf-8",
    )


def render_tree_readme(*, source_lang: str, target_lang: str) -> str:
    return "\n".join(
        [
            "# Translation Tree",
            "",
            "This folder is the translator-facing tree exported from the expanded",
            "template workspace.",
            "",
            f"- Each translation unit has its own `{TRANSLATION_DOC_NAME}` file.",
            f"- Each file starts with the source `Sentence ({source_lang})`, then the",
            f"  editable `Translation ({target_lang})` block.",
            "- Wrapper-level blocks from the expanded workspace are split into smaller",
            "  translator-facing units whenever the source structure allows it.",
            "- Keep every placeholder shown in the sentence, such as `{name}`. You",
            "  may reorder placeholders for grammar; sync converts them back to Jinja",
            "  variables.",
            "- Machine metadata is collapsed at the bottom of each file and should not",
            "  be edited manually.",
            "- If a translation file is deleted or its markdown block is broken, ask a",
            "  maintainer to refresh the translation tree from the expanded template.",
            "- CI applies translator edits back into a generated template copy and",
            "  publishes review artifacts.",
            "",
        ]
    )
