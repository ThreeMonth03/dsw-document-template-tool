"""Build auditable evidence for one DSW render-regression runtime."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .regression_evidence import (
    KnowledgeModelEvidence,
    load_regression_evidence_config,
    validate_regression_evidence_config,
)
from .translation_repository import DswPreviewRuntime, load_preview_runtimes

RUNTIME_EVIDENCE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CoverageEvidence:
    """Complete generated-fixture coverage for one fixture group."""

    name: str
    selected_cases: int
    covered_branches: int
    expected_branches: int
    complete: bool


@dataclass(frozen=True)
class VersionEvidence:
    """Regression and PDF evidence for one template version."""

    version: str
    regression_passed: bool
    fixture_count: int
    coverage: tuple[CoverageEvidence, ...]
    preview_pdf: str | None
    preview_pdf_bytes: int | None
    issues: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeEvidence:
    """Auditable render result for one document-template metamodel runtime."""

    schema_version: int
    passed: bool
    runtime: dict[str, str]
    knowledge_model: dict[str, str]
    versions: tuple[VersionEvidence, ...]


def collect_runtime_evidence(
    *,
    compat_config: Path,
    evidence_config: Path,
    metamodel_version: str,
    plan_path: Path,
    preview_root: Path,
    regression_root: Path,
    source_template_id: str,
    translation_locale: str,
) -> RuntimeEvidence:
    """Collect strict regression, coverage, KM, and preview evidence."""

    runtimes = load_preview_runtimes(compat_config)
    evidence_config_payload = load_regression_evidence_config(evidence_config)
    validate_regression_evidence_config(evidence_config_payload, runtimes)
    runtime = _runtime_for_metamodel(runtimes, metamodel_version)
    knowledge_model = evidence_config_payload.knowledge_model_for_runtime(runtime)
    versions = tuple(
        _collect_version_evidence(
            version=version,
            regression_root=regression_root,
            preview_root=preview_root,
            source_template_id=source_template_id,
            translation_locale=translation_locale,
        )
        for version in _planned_versions(plan_path, metamodel_version)
    )
    return RuntimeEvidence(
        schema_version=RUNTIME_EVIDENCE_SCHEMA_VERSION,
        passed=bool(versions) and all(not version.issues for version in versions),
        runtime={
            "metamodel_key": runtime.metamodel_key,
            "metamodel_version": runtime.metamodel_version,
            "dsw_version": runtime.dsw_version,
            "tdk_version": runtime.tdk_version,
        },
        knowledge_model=_knowledge_model_payload(knowledge_model),
        versions=versions,
    )


def write_runtime_evidence(report: RuntimeEvidence, output_dir: Path) -> tuple[Path, Path]:
    """Write machine-readable JSON and maintainer-facing Markdown reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evidence.json"
    markdown_path = output_dir / "evidence.md"
    json_path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_runtime_evidence(report), encoding="utf-8")
    return json_path, markdown_path


def render_runtime_evidence(report: RuntimeEvidence) -> str:
    """Render one concise runtime-evidence Markdown report."""

    runtime = report.runtime
    knowledge_model = report.knowledge_model
    lines = [
        f"# Runtime Evidence: metamodel {runtime['metamodel_version']}",
        "",
        f"Status: **{'passed' if report.passed else 'failed'}**",
        "",
        "## Proven Runtime",
        "",
        "| DSW | TDK | Document-template metamodel |",
        "| --- | --- | --- |",
        f"| {runtime['dsw_version']} | {runtime['tdk_version']} | {runtime['metamodel_version']} |",
        "",
        "## Knowledge Model",
        "",
        "| Package | Version | KM metamodel | SHA-256 | Source |",
        "| --- | --- | --- | --- | --- |",
        f"| `{knowledge_model['package_id']}` | {knowledge_model['version']} | "
        f"{knowledge_model['metamodel_version']} | `{knowledge_model['sha256']}` | "
        f"[official package]({knowledge_model['source_url']}) |",
        "",
        "## Version Results",
        "",
        "| Template | Regression | Fixtures | Coverage | PDF |",
        "| --- | --- | ---: | --- | --- |",
    ]
    issues: list[str] = []
    for version in report.versions:
        coverage = (
            "<br>".join(
                f"{item.name}: {item.covered_branches}/{item.expected_branches}"
                for item in version.coverage
            )
            or "missing"
        )
        pdf = (
            f"{version.preview_pdf_bytes} bytes"
            if version.preview_pdf_bytes is not None
            else "missing"
        )
        lines.append(
            f"| {version.version} | {'passed' if version.regression_passed else 'failed'} | "
            f"{version.fixture_count} | {coverage} | {pdf} |"
        )
        issues.extend(f"`{version.version}`: {issue}" for issue in version.issues)
    if issues:
        lines.extend(("", "## Issues", "", *(f"- {issue}" for issue in issues)))
    return "\n".join((*lines, ""))


def _collect_version_evidence(
    *,
    version: str,
    regression_root: Path,
    preview_root: Path,
    source_template_id: str,
    translation_locale: str,
) -> VersionEvidence:
    directory = regression_root / version
    issues: list[str] = []
    report = _read_optional_object(directory / "regression_report.json", issues)
    regression_passed = report.get("passed") is True
    fixtures = report.get("fixtures")
    fixture_count = len(fixtures) if isinstance(fixtures, list) else 0
    if not regression_passed:
        issues.append("regression did not pass")
    if not isinstance(fixtures, list):
        issues.append("regression report has no fixtures list")

    coverage = _collect_coverage(directory, issues)
    pdf_path = (
        preview_root
        / source_template_id
        / version
        / translation_locale
        / "scaffold"
        / "test-project.pdf"
    )
    status_files = [
        path.name
        for path in (pdf_path.parent / "failed.json", pdf_path.parent / "skipped.json")
        if path.is_file()
    ]
    if status_files:
        issues.append(f"stale or failed preview status: {', '.join(status_files)}")
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        issues.append("strict preview PDF is missing or empty")
        preview_pdf = None
        preview_pdf_bytes = None
    else:
        preview_pdf = pdf_path.as_posix()
        preview_pdf_bytes = pdf_path.stat().st_size
    return VersionEvidence(
        version=version,
        regression_passed=regression_passed,
        fixture_count=fixture_count,
        coverage=coverage,
        preview_pdf=preview_pdf,
        preview_pdf_bytes=preview_pdf_bytes,
        issues=tuple(issues),
    )


def _collect_coverage(directory: Path, issues: list[str]) -> tuple[CoverageEvidence, ...]:
    coverage: list[CoverageEvidence] = []
    for path in sorted(directory.glob("*-coverage.json")):
        payload = _read_optional_object(path, issues)
        try:
            item = CoverageEvidence(
                name=path.name.removesuffix("-coverage.json"),
                selected_cases=_required_int(payload, "selected_case_count"),
                covered_branches=_required_int(payload, "covered_branch_count"),
                expected_branches=_required_int(payload, "expected_branch_count"),
                complete=_required_bool(payload, "complete"),
            )
        except ValueError as exc:
            issues.append(f"invalid coverage report {path.name}: {exc}")
            continue
        coverage.append(item)
        if not item.complete or item.covered_branches != item.expected_branches:
            issues.append(
                f"incomplete coverage in {path.name}: "
                f"{item.covered_branches}/{item.expected_branches}"
            )
    if not coverage:
        issues.append("no generated-fixture coverage report")
    return tuple(coverage)


def _planned_versions(plan_path: Path, metamodel_version: str) -> tuple[str, ...]:
    payload = _read_object(plan_path)
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError(f"Regression plan {plan_path} has no candidates list")
    versions = tuple(
        str(candidate["version"])
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("recommended") is True
        and candidate.get("metamodel_version") == metamodel_version
        and isinstance(candidate.get("version"), str)
    )
    if not versions:
        raise ValueError(
            f"Regression plan has no recommended versions for metamodel {metamodel_version}"
        )
    return versions


def _runtime_for_metamodel(
    runtimes: tuple[DswPreviewRuntime, ...], metamodel_version: str
) -> DswPreviewRuntime:
    matches = [runtime for runtime in runtimes if runtime.metamodel_version == metamodel_version]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one runtime for metamodel {metamodel_version}, found {len(matches)}"
        )
    return matches[0]


def _knowledge_model_payload(evidence: KnowledgeModelEvidence) -> dict[str, str]:
    return {
        "key": evidence.key,
        "path": evidence.path.as_posix(),
        "package_id": evidence.package_id,
        "version": evidence.version,
        "metamodel_version": evidence.metamodel_version,
        "source_url": evidence.source_url,
        "sha256": evidence.sha256,
    }


def _read_optional_object(path: Path, issues: list[str]) -> dict[str, Any]:
    try:
        return _read_object(path)
    except (OSError, ValueError) as exc:
        issues.append(f"could not read {path.name}: {exc}")
        return {}


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if type(value) is not int:
        raise ValueError(f"expected integer {key!r}")
    return value


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"expected boolean {key!r}")
    return value
