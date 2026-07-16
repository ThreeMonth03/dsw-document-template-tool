"""Tests for complete DSW runtime evidence reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dsw_document_template_tool.runtime_evidence import (
    collect_runtime_evidence,
    render_runtime_evidence,
    write_runtime_evidence,
)


def test_runtime_evidence_requires_regression_coverage_and_pdf(tmp_path: Path) -> None:
    """A runtime passes only when every planned version has all three proofs."""

    paths = _write_inputs(tmp_path)
    _write_version_outputs(tmp_path, include_pdf=True)

    report = collect_runtime_evidence(**paths)
    json_path, markdown_path = write_runtime_evidence(report, tmp_path / "evidence")

    assert report.passed is True
    assert report.runtime["dsw_version"] == "4.30"
    assert report.knowledge_model["package_id"] == "dsw:root:2.7.0"
    assert report.versions[0].coverage[0].complete is True
    assert json.loads(json_path.read_text(encoding="utf-8"))["passed"] is True
    assert "Status: **passed**" in markdown_path.read_text(encoding="utf-8")


def test_runtime_evidence_reports_missing_strict_preview(tmp_path: Path) -> None:
    """Regression equality alone must not hide a missing package preview PDF."""

    paths = _write_inputs(tmp_path)
    _write_version_outputs(tmp_path, include_pdf=False)

    report = collect_runtime_evidence(**paths)

    assert report.passed is False
    assert "strict preview PDF is missing or empty" in report.versions[0].issues
    assert "Status: **failed**" in render_runtime_evidence(report)


def _write_inputs(tmp_path: Path) -> dict[str, object]:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    bundle = tmp_path / "fixtures/root.km"
    bundle.parent.mkdir()
    bundle.write_text(
        json.dumps(
            {
                "id": "dsw:root:2.7.0",
                "metamodelVersion": 19,
                "version": "2.7.0",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    checksum = hashlib.sha256(bundle.read_bytes()).hexdigest()
    compat = config_dir / "dsw-compat.yml"
    compat.write_text(
        """
schema_version: 1
runtimes:
  - metamodel_key: "18-0"
    metamodel_version: "18.0"
    dsw_version: "4.30"
    tdk_version: "4.30.2"
    min_version: "v1.30.0"
    max_version: null
    upstream_template_artifact_refs: "v1.30.0+"
""".lstrip(),
        encoding="utf-8",
    )
    evidence = config_dir / "regression-evidence.yml"
    evidence.write_text(
        f"""
schema_version: 1
knowledge_models:
  root:
    path: ../fixtures/root.km
    package_id: dsw:root:2.7.0
    version: "2.7.0"
    metamodel_version: "19"
    source_url: https://example.test/root
    sha256: {checksum}
runtime_knowledge_models:
  "18-0": root
""".lstrip(),
        encoding="utf-8",
    )
    plan = tmp_path / "regression-plan.json"
    plan.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "version": "v1.30.1",
                        "metamodel_version": "18.0",
                        "recommended": True,
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "compat_config": compat,
        "evidence_config": evidence,
        "metamodel_version": "18.0",
        "plan_path": plan,
        "preview_root": tmp_path / "project-render",
        "regression_root": tmp_path / "preview",
        "source_template_id": "dsw-science-europe",
        "translation_locale": "zh-Hant",
    }


def _write_version_outputs(tmp_path: Path, *, include_pdf: bool) -> None:
    regression_dir = tmp_path / "preview/v1.30.1"
    regression_dir.mkdir(parents=True)
    (regression_dir / "regression_report.json").write_text(
        json.dumps({"passed": True, "fixtures": [{"passed": True}]}) + "\n",
        encoding="utf-8",
    )
    (regression_dir / "random-project-coverage.json").write_text(
        json.dumps(
            {
                "selected_case_count": 35,
                "covered_branch_count": 1136,
                "expected_branch_count": 1136,
                "complete": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if include_pdf:
        pdf = (
            tmp_path / "project-render/dsw-science-europe/v1.30.1/zh-Hant/scaffold/test-project.pdf"
        )
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"%PDF-1.7\n")
