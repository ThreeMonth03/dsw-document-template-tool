"""Merge translator edits from an older tree into a regenerated tree."""

from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
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
from .outline import refresh_outline_markdown
from .placeholders import (
    contains_raw_jinja_in_translation,
    extract_translator_placeholder_names,
    translation_placeholder_counts,
)

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
class ReuseIndexes:
    """Lookup tables for translations that are safe to migrate."""

    by_key: dict[tuple[str, str], TranslationCandidate]
    by_hash: dict[str, TranslationCandidate]
    by_sentence: dict[str, TranslationCandidate]


@dataclass(frozen=True)
class CandidateMatch:
    """One old-tree candidate selected for one new-tree unit."""

    candidate: TranslationCandidate
    kind: str


@dataclass(frozen=True)
class TranslationMergeReport:
    """Summary of one old-tree to new-tree translation merge."""

    total_units: int
    preserved_units: int
    migrated_units: int
    untranslated_units: int
    skipped_unsafe_old_units: int
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
    allow_sentence_matches: bool = False,
) -> TranslationMergeReport:
    """Copy a regenerated tree and fill blank translations from an older tree.

    Matching is intentionally conservative. Exact `(source_file, unit_key)` can
    reuse a translation only when the unit source hash is unchanged, then unique
    source hash can recover moved but byte-identical source units. Visible
    sentence matches are intentionally disabled by default because they cannot
    prove that the underlying Jinja/HTML structure is still equivalent.
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

    reusable_old_candidates = [
        candidate for candidate in old_candidates if _is_reusable_translation(candidate)
    ]
    translated_old_units = [
        candidate for candidate in old_candidates if candidate.translation_text.strip()
    ]
    skipped_unsafe_old_units = len(translated_old_units) - len(reusable_old_candidates)

    reuse_indexes = _build_reuse_indexes(
        reusable_old_candidates,
        allow_sentence_matches=allow_sentence_matches,
    )

    preserved = 0
    migrated = 0
    match_counts: Counter[str] = Counter()

    for candidate in new_candidates:
        if candidate.translation_text.strip():
            preserved += 1
            continue

        match = _find_reusable_match(
            candidate,
            reuse_indexes=reuse_indexes,
            allow_sentence_matches=allow_sentence_matches,
        )
        if match is None:
            continue

        replace_translation_text(
            document_path=output_dir / candidate.document_path,
            target_lang=target_lang,
            translation_text=match.candidate.translation_text,
        )
        migrated += 1
        match_counts[match.kind] += 1

    report = TranslationMergeReport(
        total_units=len(new_candidates),
        preserved_units=preserved,
        migrated_units=migrated,
        untranslated_units=len(new_candidates) - preserved - migrated,
        skipped_unsafe_old_units=skipped_unsafe_old_units,
        exact_key_matches=match_counts["exact-key"],
        source_hash_matches=match_counts["source-hash"],
        sentence_matches=match_counts["sentence"],
    )
    report_path = output_dir / MERGE_REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    refresh_outline_markdown(
        tree_dir=output_dir,
        source_lang=source_lang,
        target_lang=target_lang,
    )
    return report


def _load_candidates(
    *,
    tree_dir: Path,
    source_lang: str,
    target_lang: str,
    forgiving: bool,
) -> list[TranslationCandidate]:
    try:
        manifest = load_tree_manifest(tree_dir)
    except TranslationTreeError:
        if forgiving:
            return []
        raise
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


def _build_reuse_indexes(
    candidates: list[TranslationCandidate],
    *,
    allow_sentence_matches: bool,
) -> ReuseIndexes:
    by_sentence: dict[str, TranslationCandidate] = {}
    if allow_sentence_matches:
        by_sentence = _unique_index(
            candidates,
            key=lambda candidate: _normalize_sentence(candidate.sentence_text),
        )
    return ReuseIndexes(
        by_key={(candidate.source_file, candidate.unit_key): candidate for candidate in candidates},
        by_hash=_unique_index(
            candidates,
            key=lambda candidate: candidate.unit_source_hash,
        ),
        by_sentence=by_sentence,
    )


def _find_reusable_match(
    candidate: TranslationCandidate,
    *,
    reuse_indexes: ReuseIndexes,
    allow_sentence_matches: bool,
) -> CandidateMatch | None:
    key_match = reuse_indexes.by_key.get((candidate.source_file, candidate.unit_key))
    if key_match is not None and key_match.unit_source_hash == candidate.unit_source_hash:
        return CandidateMatch(candidate=key_match, kind="exact-key")

    hash_match = reuse_indexes.by_hash.get(candidate.unit_source_hash)
    if hash_match is not None:
        return CandidateMatch(candidate=hash_match, kind="source-hash")

    if not allow_sentence_matches:
        return None

    sentence_match = reuse_indexes.by_sentence.get(_normalize_sentence(candidate.sentence_text))
    if sentence_match is None:
        return None
    return CandidateMatch(candidate=sentence_match, kind="sentence")


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


def _is_reusable_translation(candidate: TranslationCandidate) -> bool:
    """Return whether an old translation can be migrated without repair."""

    translation_text = candidate.translation_text
    if not translation_text.strip():
        return False
    if contains_raw_jinja_in_translation(translation_text):
        return False

    required_placeholders = Counter(extract_translator_placeholder_names(candidate.sentence_text))
    if required_placeholders != translation_placeholder_counts(translation_text):
        return False

    return True


def _normalize_sentence(sentence_text: str) -> str:
    return " ".join(sentence_text.split())
