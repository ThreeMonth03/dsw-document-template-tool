"""Write and compare deterministic regression artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..html_diff import build_unified_diff, normalize_html
from ..models import RegressionReport, RenderArtifact, ResolvedSubject


def write_render_artifact(
    *,
    fixture_output_dir: Path,
    subject: ResolvedSubject,
    raw_html: str,
    ignore_patterns: list[str],
) -> RenderArtifact:
    """Persist raw and normalized HTML for one regression subject."""

    raw_path = fixture_output_dir / f"{subject.label}.raw.html"
    normalized_path = fixture_output_dir / f"{subject.label}.normalized.html"
    raw_path.write_text(raw_html, encoding="utf-8")
    normalized_path.write_text(
        normalize_html(raw_html, ignore_patterns=ignore_patterns) + "\n",
        encoding="utf-8",
    )
    return RenderArtifact(
        raw_path=raw_path,
        normalized_path=normalized_path,
        subject_label=subject.label,
        template_reference=subject.display_id,
    )


def compare_render_artifacts(
    *,
    fixture_output_dir: Path,
    baseline: RenderArtifact,
    candidate: RenderArtifact,
) -> tuple[bool, Path | None]:
    """Compare normalized artifacts and write a unified diff on mismatch."""

    baseline_html = baseline.normalized_path.read_text(encoding="utf-8")
    candidate_html = candidate.normalized_path.read_text(encoding="utf-8")
    if baseline_html == candidate_html:
        return True, None

    diff_path = fixture_output_dir / "diff.diff"
    diff_path.write_text(
        build_unified_diff(
            baseline_html,
            candidate_html,
            baseline_label=baseline.template_reference,
            candidate_label=candidate.template_reference,
        )
        + "\n",
        encoding="utf-8",
    )
    return False, diff_path


def serialize_regression_report(report: RegressionReport) -> dict[str, Any]:
    """Convert a regression report into its stable JSON representation."""

    return {
        "mode": report.mode,
        "output_dir": str(report.output_dir),
        "passed": report.passed,
        "fixtures": [
            {
                "fixture_name": result.fixture_name,
                "project_uuid": result.project_uuid,
                "equal": result.equal,
                "baseline": _serialize_render_artifact(result.baseline),
                "candidate": _serialize_render_artifact(result.candidate),
                "diff_path": None if result.diff_path is None else str(result.diff_path),
            }
            for result in report.fixture_results
        ],
    }


def _serialize_render_artifact(artifact: RenderArtifact) -> dict[str, str]:
    return {
        "subject_label": artifact.subject_label,
        "template_reference": artifact.template_reference,
        "raw_path": str(artifact.raw_path),
        "normalized_path": str(artifact.normalized_path),
    }
