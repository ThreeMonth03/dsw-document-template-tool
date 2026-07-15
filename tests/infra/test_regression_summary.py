"""Tests for the maintainer-facing render-regression summary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_summary_reports_versioned_results_and_branch_coverage(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Actions should expose complete regression evidence without artifacts."""

    output_dir = tmp_path / "preview"
    _write_regression_report(
        output_dir / "v1.30.0",
        version="1.30.0",
        equal=(True, False),
    )
    _write_coverage_report(
        output_dir / "v1.30.0",
        selected=35,
        covered=1136,
        expected=1136,
        complete=True,
    )
    _write_regression_report(
        output_dir / "v1.30.1",
        version="1.30.1",
        equal=(True, True, True),
    )
    _write_coverage_report(
        output_dir / "v1.30.1",
        selected=35,
        covered=1136,
        expected=1136,
        complete=True,
    )
    summary_path = tmp_path / "github-summary.md"
    env = os.environ.copy()
    env["GITHUB_STEP_SUMMARY"] = str(summary_path)

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "summarize_regression_coverage.py"),
            "--output-dir",
            str(output_dir),
            "--title",
            "Metamodel 18.0 Render Regression",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == summary_path.read_text(encoding="utf-8")
    assert "## Metamodel 18.0 Render Regression" in result.stdout
    assert "| v1.30.0 | Failed (1 different) | 2 |" in result.stdout
    assert "random-project: 35" in result.stdout
    assert "random-project: 1136/1136 (complete)" in result.stdout
    assert "| v1.30.1 | Passed | 3 |" in result.stdout
    assert "random-project: 35" in result.stdout
    assert "random-project: 1136/1136 (complete)" in result.stdout


def test_summary_surfaces_unreadable_reports_without_failing(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """A diagnostic summary must not replace the original regression failure."""

    output_dir = tmp_path / "preview"
    broken_dir = output_dir / "v1.30.1"
    broken_dir.mkdir(parents=True)
    (broken_dir / "regression_report.json").write_text("{broken\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "summarize_regression_coverage.py"),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "| v1.30.1 | Unknown | - | Not reported | Not reported |" in result.stdout
    assert "could not read `regression_report.json`: invalid JSON at line 1" in result.stdout


def test_summary_explains_when_regression_produced_no_report(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Early DSW failures should leave an explicit empty-summary message."""

    output_dir = tmp_path / "preview"
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "summarize_regression_coverage.py"),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"No regression reports were found under `{output_dir}`." in result.stdout


def _write_regression_report(
    output_dir: Path,
    *,
    version: str,
    equal: tuple[bool, ...],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fixtures = [
        {
            "fixture_name": f"fixture-{index}",
            "equal": fixture_equal,
            "candidate": {
                "template_reference": f"ci:science-europe-expanded:{version}",
            },
        }
        for index, fixture_equal in enumerate(equal)
    ]
    payload = {
        "passed": all(equal),
        "fixtures": fixtures,
    }
    (output_dir / "regression_report.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_coverage_report(
    output_dir: Path,
    *,
    selected: int,
    covered: int,
    expected: int,
    complete: bool,
) -> None:
    payload = {
        "selected_case_count": selected,
        "covered_branch_count": covered,
        "expected_branch_count": expected,
        "complete": complete,
    }
    (output_dir / "random-project-coverage.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
