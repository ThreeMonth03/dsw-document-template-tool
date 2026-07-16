"""Read-only consistency review across translated template version branches."""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from .._translation_tree.document import (
    parse_sentence_markdown,
    parse_translation_markdown,
)
from .._translation_tree.manifest import TREE_MANIFEST_PATH
from .errors import TranslationRepositoryError
from .models import TranslationRepositoryConfig
from .paths import version_branch, version_paths
from .policy import version_policy_decision
from .versions import version_sort_key

ConsistencyIssue = Literal["translation-gap", "wording-drift"]
SourceMatch = Literal["exact-source", "visible-source-only"]
CONSISTENCY_REPORT_SCHEMA_VERSION = 1
WORKING_LIFECYCLE_STATES = frozenset({"active", "maintenance"})


@dataclass(frozen=True)
class TranslationVersionRecord:
    """One source/target pair read from a version branch translation unit."""

    version: str
    branch: str
    document_path: str
    source_file: str
    unit_key: str
    source_hash: str
    source_sentence: str
    translation: str


@dataclass(frozen=True)
class TranslationConsistencyFinding:
    """One shared source sentence that needs cross-version human review."""

    source_sentence: str
    source_match: SourceMatch
    issues: tuple[ConsistencyIssue, ...]
    records: tuple[TranslationVersionRecord, ...]


@dataclass(frozen=True)
class TranslationConsistencyReport:
    """Stable machine-readable result of one cross-version consistency scan."""

    schema_version: int
    versions: tuple[str, ...]
    units_by_version: dict[str, int]
    shared_source_count: int
    findings: tuple[TranslationConsistencyFinding, ...]

    @property
    def translation_gap_count(self) -> int:
        """Return the number of shared sources with blank/nonblank target drift."""

        return sum("translation-gap" in finding.issues for finding in self.findings)

    @property
    def wording_drift_count(self) -> int:
        """Return the number of shared sources with different nonblank targets."""

        return sum("wording-drift" in finding.issues for finding in self.findings)


def default_consistency_versions(config: TranslationRepositoryConfig) -> list[str]:
    """Return active and maintenance versions expected to have editable branches."""

    return [
        version
        for version in config.template.supported_versions
        if version_policy_decision(config, version).state in WORKING_LIFECYCLE_STATES
    ]


def fetch_version_branches(*, repo: Path, config: TranslationRepositoryConfig) -> None:
    """Refresh remote-tracking refs for the configured version branch prefix."""

    prefix = config.branches.version_branch_prefix
    refspec = f"+refs/heads/{prefix}*:refs/remotes/origin/{prefix}*"
    _git(Path(repo).resolve(), "fetch", "--prune", "origin", refspec)


def inspect_translation_repository(
    *,
    repo: Path,
    config: TranslationRepositoryConfig,
    versions: list[str] | None = None,
) -> TranslationConsistencyReport:
    """Read configured version branches and build a consistency report."""

    selected_versions = versions or default_consistency_versions(config)
    records_by_version = {
        version: load_version_records(repo=repo, config=config, version=version)
        for version in selected_versions
    }
    return analyze_translation_records(records_by_version)


def load_version_records(
    *,
    repo: Path,
    config: TranslationRepositoryConfig,
    version: str,
) -> tuple[TranslationVersionRecord, ...]:
    """Read one version's tree from its remote or local Git branch without checkout."""

    repo = Path(repo).resolve()
    branch = version_branch(config, version)
    ref = _resolve_branch_ref(repo=repo, branch=branch)
    tree_root = version_paths(config, version).translation_tree_dir.as_posix()
    archive = _git(repo, "archive", "--format=tar", ref, tree_root, text=False).stdout
    return _records_from_archive(
        archive=archive,
        branch=branch,
        tree_root=tree_root,
        version=version,
        source_lang=config.translation.source_language,
        target_lang=config.translation.target_language,
    )


def analyze_translation_records(
    records_by_version: dict[str, tuple[TranslationVersionRecord, ...]],
) -> TranslationConsistencyReport:
    """Compare records by normalized visible source and return review findings."""

    grouped: dict[str, list[TranslationVersionRecord]] = defaultdict(list)
    units_by_version: dict[str, int] = {}
    for version, records in records_by_version.items():
        units_by_version[version] = len(records)
        for record in records:
            grouped[_normalize_source(record.source_sentence)].append(record)

    shared_source_count = 0
    findings: list[TranslationConsistencyFinding] = []
    for source_key, records in grouped.items():
        if len({record.version for record in records}) < 2:
            continue
        shared_source_count += 1
        normalized_targets = {
            _normalize_translation(record.translation)
            for record in records
            if record.translation.strip()
        }
        issues: list[ConsistencyIssue] = []
        if normalized_targets and any(not record.translation.strip() for record in records):
            issues.append("translation-gap")
        if len(normalized_targets) > 1:
            issues.append("wording-drift")
        if not issues:
            continue

        ordered_records = tuple(
            sorted(records, key=lambda item: (version_sort_key(item.version), item.document_path))
        )
        source_hashes = {record.source_hash for record in records}
        findings.append(
            TranslationConsistencyFinding(
                source_sentence=source_key,
                source_match=("exact-source" if len(source_hashes) == 1 else "visible-source-only"),
                issues=tuple(issues),
                records=ordered_records,
            )
        )

    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda item: (
                item.source_match != "exact-source",
                item.issues,
                item.source_sentence.casefold(),
            ),
        )
    )
    versions = tuple(sorted(records_by_version, key=version_sort_key))
    return TranslationConsistencyReport(
        schema_version=CONSISTENCY_REPORT_SCHEMA_VERSION,
        versions=versions,
        units_by_version={version: units_by_version[version] for version in versions},
        shared_source_count=shared_source_count,
        findings=ordered_findings,
    )


def report_as_json(report: TranslationConsistencyReport) -> str:
    """Serialize a report with explicit summary counts and stable ordering."""

    payload = asdict(report)
    payload["summary"] = {
        "finding_count": len(report.findings),
        "translation_gap_count": report.translation_gap_count,
        "wording_drift_count": report.wording_drift_count,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_consistency_markdown(
    report: TranslationConsistencyReport,
    *,
    max_findings: int | None = None,
) -> str:
    """Render a concise review report for Actions summaries and artifacts."""

    findings = report.findings if max_findings is None else report.findings[:max_findings]
    lines = [
        "# Cross-Version Translation Consistency",
        "",
        "This read-only report compares visible source sentences across active and",
        "maintenance version branches. It does not change translations or relax the",
        "exact-source migration safety checks.",
        "",
        f"- Versions: {', '.join(f'`{version}`' for version in report.versions)}",
        f"- Shared visible sources: {report.shared_source_count}",
        f"- Translation gaps: {report.translation_gap_count}",
        f"- Wording drifts: {report.wording_drift_count}",
        "",
    ]
    if not report.findings:
        lines.extend(["No cross-version translation differences need review.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "`exact-source` means the executable source hash also matches.",
            "`visible-source-only` is a terminology hint only; Jinja or HTML may differ.",
            "",
        ]
    )
    for index, finding in enumerate(findings, start=1):
        issues = ", ".join(finding.issues)
        lines.extend(
            [
                f"## {index}. {issues} ({finding.source_match})",
                "",
                f"> {_markdown_single_line(finding.source_sentence)}",
                "",
                "| Version | Translation | Location |",
                "| --- | --- | --- |",
            ]
        )
        for record in finding.records:
            translation = record.translation.strip() or "_(blank)_"
            table_translation = _markdown_table_text(translation)
            lines.append(f"| `{record.version}` | {table_translation} | `{record.document_path}` |")
        lines.append("")

    hidden_count = len(report.findings) - len(findings)
    if hidden_count:
        lines.extend(
            [
                f"_The Actions summary omits {hidden_count} additional findings. "
                "Download the report artifact for the complete list._",
                "",
            ]
        )
    return "\n".join(lines)


def _records_from_archive(
    *,
    archive: bytes,
    branch: str,
    tree_root: str,
    version: str,
    source_lang: str,
    target_lang: str,
) -> tuple[TranslationVersionRecord, ...]:
    manifest_name = (PurePosixPath(tree_root) / TREE_MANIFEST_PATH).as_posix()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        manifest = _read_json_member(bundle, manifest_name)
        if manifest.get("source_lang") != source_lang or manifest.get("target_lang") != target_lang:
            raise TranslationRepositoryError(
                f"Translation tree on {branch} has unexpected language metadata"
            )
        units = manifest.get("units")
        if not isinstance(units, list):
            raise TranslationRepositoryError(
                f"Translation tree manifest on {branch} must contain a units list"
            )

        records = [
            _record_from_manifest_unit(
                bundle=bundle,
                branch=branch,
                tree_root=tree_root,
                version=version,
                source_lang=source_lang,
                target_lang=target_lang,
                unit=unit,
            )
            for unit in units
        ]
    return tuple(records)


def _record_from_manifest_unit(
    *,
    bundle: tarfile.TarFile,
    branch: str,
    tree_root: str,
    version: str,
    source_lang: str,
    target_lang: str,
    unit: object,
) -> TranslationVersionRecord:
    if not isinstance(unit, dict):
        raise TranslationRepositoryError(f"Invalid translation unit metadata on {branch}")
    document_path = _required_manifest_str(unit, "document_path", branch)
    markdown = _read_text_member(
        bundle,
        (PurePosixPath(tree_root) / document_path).as_posix(),
    )
    location = f"{branch}:{tree_root}/{document_path}"
    return TranslationVersionRecord(
        version=version,
        branch=branch,
        document_path=(PurePosixPath(tree_root) / document_path).as_posix(),
        source_file=_required_manifest_str(unit, "source_file", branch),
        unit_key=_required_manifest_str(unit, "unit_key", branch),
        source_hash=_required_manifest_str(unit, "unit_source_hash", branch),
        source_sentence=parse_sentence_markdown(
            markdown_text=markdown,
            location=location,
            source_lang=source_lang,
        ),
        translation=parse_translation_markdown(
            markdown_text=markdown,
            location=location,
            source_lang=source_lang,
            target_lang=target_lang,
        ),
    )


def _resolve_branch_ref(*, repo: Path, branch: str) -> str:
    for ref in (f"refs/remotes/origin/{branch}", f"refs/heads/{branch}"):
        result = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if result.returncode == 0:
            return ref
    raise TranslationRepositoryError(
        f"Missing version branch {branch!r}; fetch remote branches or run version refresh first"
    )


def _git(
    repo: Path,
    *args: str,
    text: bool = True,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=text,
        check=False,
    )
    if result.returncode != 0 and args[:3] != ("rev-parse", "--verify", "--quiet"):
        stderr = result.stderr.strip() if text else result.stderr.decode(errors="replace").strip()
        raise TranslationRepositoryError(
            f"git {' '.join(args)} failed in {repo}: {stderr or 'unknown Git error'}"
        )
    return result


def _read_json_member(bundle: tarfile.TarFile, name: str) -> dict:
    try:
        payload = json.loads(_read_text_member(bundle, name))
    except json.JSONDecodeError as exc:
        raise TranslationRepositoryError(f"Invalid JSON in archived {name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TranslationRepositoryError(f"Archived {name} must contain a JSON object")
    return payload


def _read_text_member(bundle: tarfile.TarFile, name: str) -> str:
    try:
        member = bundle.getmember(name)
    except KeyError as exc:
        raise TranslationRepositoryError(f"Missing archived translation-tree file: {name}") from exc
    handle = bundle.extractfile(member)
    if handle is None:
        raise TranslationRepositoryError(f"Archived translation-tree path is not a file: {name}")
    return handle.read().decode("utf-8")


def _required_manifest_str(unit: dict, key: str, branch: str) -> str:
    value = unit.get(key)
    if not isinstance(value, str) or not value:
        raise TranslationRepositoryError(f"Invalid {key} in translation manifest on {branch}")
    return value


def _normalize_source(value: str) -> str:
    return " ".join(value.split())


def _normalize_translation(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def _markdown_single_line(value: str) -> str:
    return value.replace("\n", " ")


def _markdown_table_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")
