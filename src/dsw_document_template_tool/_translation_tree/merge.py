"""Merge translator edits from an older tree into a regenerated tree."""

from __future__ import annotations

import json
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .document import (
    parse_sentence_text,
    parse_translation_document,
    replace_translation_text,
)
from .filesystem import reset_dir
from .manifest import TREE_MANIFEST_PATH, load_tree_manifest
from .models import TranslationTreeError

MERGE_REPORT_PATH = Path(".translation-tree") / "merge-report.json"


@dataclass(frozen=True)
class TranslationCandidate:
    """One reusable translation from an older translation tree."""

    source_file: str
    unit_key: str
    unit_source_hash: str
    document_path: str
    sentence_text: str
    translation_text: str


@dataclass(frozen=True)
class TranslationMergeReport:
    """Summary of one old-tree to new-tree translation merge."""

    total_units: int
    preserved_units: int
    migrated_units: int
    untranslated_units: int
    exact_key_matches: int
    source_hash_matches: int
    sentence_matches: int


def merge_translation_tree(
    *,
    old_tree_dir: Path,
    new_tree_dir: Path,
    output_dir: Path,
    source_lang: str,
    target_lang: str,
) -> TranslationMergeReport:
    """Copy a regenerated tree and fill blank translations from an older tree.

    Matching is intentionally conservative. Exact `(source_file, unit_key)` wins,
    then unique source hash, then unique visible source sentence. Ambiguous
    hash/sentence matches are ignored rather than guessed.
    """

    old_tree_dir = Path(old_tree_dir).resolve()
    new_tree_dir = Path(new_tree_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if old_tree_dir == output_dir:
        raise TranslationTreeError("--output must differ from --old-tree")

    if new_tree_dir != output_dir:
        reset_dir(output_dir)
        shutil.copytree(new_tree_dir, output_dir, dirs_exist_ok=True)

    old_candidates = _load_candidates(
        tree_dir=old_tree_dir,
        source_lang=source_lang,
        target_lang=target_lang,
        forgiving=True,
    )
    new_candidates = _load_candidates(
        tree_dir=output_dir,
        source_lang=source_lang,
        target_lang=target_lang,
        forgiving=False,
    )

    by_key = {
        (candidate.source_file, candidate.unit_key): candidate
        for candidate in old_candidates
        if candidate.translation_text.strip()
    }
    by_hash = _unique_index(
        old_candidates,
        key=lambda candidate: candidate.unit_source_hash,
    )
    by_sentence = _unique_index(
        old_candidates,
        key=lambda candidate: _normalize_sentence(candidate.sentence_text),
    )

    preserved = 0
    migrated = 0
    exact_key_matches = 0
    source_hash_matches = 0
    sentence_matches = 0

    for candidate in new_candidates:
        if candidate.translation_text.strip():
            preserved += 1
            continue

        match = by_key.get((candidate.source_file, candidate.unit_key))
        match_kind = "exact-key" if match is not None else ""
        if match is None:
            match = by_hash.get(candidate.unit_source_hash)
            match_kind = "source-hash" if match is not None else ""
        if match is None:
            match = by_sentence.get(_normalize_sentence(candidate.sentence_text))
            match_kind = "sentence" if match is not None else ""
        if match is None or not match.translation_text.strip():
            continue

        replace_translation_text(
            document_path=output_dir / candidate.document_path,
            target_lang=target_lang,
            translation_text=match.translation_text,
        )
        migrated += 1
        if match_kind == "exact-key":
            exact_key_matches += 1
        elif match_kind == "source-hash":
            source_hash_matches += 1
        elif match_kind == "sentence":
            sentence_matches += 1

    report = TranslationMergeReport(
        total_units=len(new_candidates),
        preserved_units=preserved,
        migrated_units=migrated,
        untranslated_units=len(new_candidates) - preserved - migrated,
        exact_key_matches=exact_key_matches,
        source_hash_matches=source_hash_matches,
        sentence_matches=sentence_matches,
    )
    report_path = output_dir / MERGE_REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def _load_candidates(
    *,
    tree_dir: Path,
    source_lang: str,
    target_lang: str,
    forgiving: bool,
) -> list[TranslationCandidate]:
    manifest = load_tree_manifest(tree_dir)
    units = manifest.get("units")
    if not isinstance(units, list):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest at {tree_dir / TREE_MANIFEST_PATH}"
        )

    candidates: list[TranslationCandidate] = []
    for unit in units:
        try:
            candidate = _candidate_from_manifest_unit(
                tree_dir=tree_dir,
                unit=unit,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        except TranslationTreeError:
            if forgiving:
                continue
            raise
        candidates.append(candidate)
    return candidates


def _candidate_from_manifest_unit(
    *,
    tree_dir: Path,
    unit: object,
    source_lang: str,
    target_lang: str,
) -> TranslationCandidate:
    if not isinstance(unit, dict):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
        )
    source_file = unit.get("source_file")
    unit_key = unit.get("unit_key")
    unit_source_hash = unit.get("unit_source_hash")
    document_path_raw = unit.get("document_path")
    if (
        not isinstance(source_file, str)
        or not isinstance(unit_key, str)
        or not isinstance(unit_source_hash, str)
        or not isinstance(document_path_raw, str)
    ):
        raise TranslationTreeError(
            f"Invalid translation-tree manifest entry at {tree_dir / TREE_MANIFEST_PATH}"
        )
    document_path = tree_dir / document_path_raw
    if not document_path.is_file():
        raise TranslationTreeError(f"Missing translation document at {document_path}")
    return TranslationCandidate(
        source_file=source_file,
        unit_key=unit_key,
        unit_source_hash=unit_source_hash,
        document_path=document_path_raw,
        sentence_text=parse_sentence_text(
            document_path=document_path,
            source_lang=source_lang,
        ),
        translation_text=parse_translation_document(
            document_path=document_path,
            source_lang=source_lang,
            target_lang=target_lang,
        ),
    )


def _unique_index(
    candidates: list[TranslationCandidate],
    *,
    key,
) -> dict[str, TranslationCandidate]:
    grouped: dict[str, list[TranslationCandidate]] = defaultdict(list)
    for candidate in candidates:
        if not candidate.translation_text.strip():
            continue
        grouped[key(candidate)].append(candidate)
    return {
        index_key: grouped_candidates[0]
        for index_key, grouped_candidates in grouped.items()
        if index_key and len(grouped_candidates) == 1
    }


def _normalize_sentence(sentence_text: str) -> str:
    return " ".join(sentence_text.split())
