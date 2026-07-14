"""Tests for deterministic regression artifact handling."""

from __future__ import annotations

from pathlib import Path

from dsw_document_template_tool._regression.artifacts import (
    compare_render_artifacts,
    serialize_regression_report,
    write_render_artifact,
)
from dsw_document_template_tool.models import (
    FixtureRegressionResult,
    RegressionReport,
    ResolvedSubject,
)


def _subject(label: str, display_id: str) -> ResolvedSubject:
    return ResolvedSubject(
        label=label,
        mode="draft",
        source_value=display_id,
        display_id=display_id,
    )


def test_artifact_comparison_writes_diff_only_for_mismatch(tmp_path: Path) -> None:
    """Raw output is preserved while normalized mismatches get one readable diff."""

    baseline = write_render_artifact(
        fixture_output_dir=tmp_path,
        subject=_subject("baseline", "dsw:template:1.0.0"),
        raw_html="<p>Baseline</p>",
        ignore_patterns=[],
    )
    candidate = write_render_artifact(
        fixture_output_dir=tmp_path,
        subject=_subject("candidate", "dsw:template:1.0.1"),
        raw_html="<p>Candidate</p>",
        ignore_patterns=[],
    )

    equal, diff_path = compare_render_artifacts(
        fixture_output_dir=tmp_path,
        baseline=baseline,
        candidate=candidate,
    )

    assert equal is False
    assert diff_path == tmp_path / "diff.diff"
    assert "dsw:template:1.0.0" in diff_path.read_text(encoding="utf-8")
    assert baseline.raw_path.read_text(encoding="utf-8") == "<p>Baseline</p>"


def test_report_serialization_has_stable_external_shape(tmp_path: Path) -> None:
    """Report JSON should expose paths and references without dataclass internals."""

    baseline = write_render_artifact(
        fixture_output_dir=tmp_path,
        subject=_subject("baseline", "baseline-id"),
        raw_html="<p>same</p>",
        ignore_patterns=[],
    )
    candidate = write_render_artifact(
        fixture_output_dir=tmp_path,
        subject=_subject("candidate", "candidate-id"),
        raw_html="<p>same</p>",
        ignore_patterns=[],
    )
    report = RegressionReport(
        mode="preview",
        output_dir=tmp_path,
        passed=True,
        fixture_results=[
            FixtureRegressionResult(
                fixture_name="empty",
                project_uuid="project-uuid",
                equal=True,
                baseline=baseline,
                candidate=candidate,
                diff_path=None,
            )
        ],
        report_path=tmp_path / "regression_report.json",
    )

    payload = serialize_regression_report(report)

    assert payload["passed"] is True
    assert payload["fixtures"][0]["candidate"]["template_reference"] == "candidate-id"
    assert payload["fixtures"][0]["diff_path"] is None
