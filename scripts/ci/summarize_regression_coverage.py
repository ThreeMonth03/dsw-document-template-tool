#!/usr/bin/env python3
"""Summarize render-regression results and generated-fixture coverage."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SummaryRow:
    """Preformatted values for one versioned regression run."""

    run: str
    regression: str
    fixtures: str
    generated_cases: str
    branch_coverage: str
    warnings: tuple[str, ...] = ()


def main() -> None:
    """Print Markdown and append it to the Actions summary when available."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, default=_environment_path("GITHUB_STEP_SUMMARY"))
    parser.add_argument("--title", default="Render Regression Coverage")
    args = parser.parse_args()

    report = render_summary(output_dir=args.output_dir, title=args.title)
    print(report, end="")
    if args.summary is not None:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        with args.summary.open("a", encoding="utf-8") as summary_file:
            summary_file.write(report)


def render_summary(*, output_dir: Path, title: str) -> str:
    """Return a concise Markdown table for reports below ``output_dir``."""

    rows = sorted(
        (_read_row(path, output_dir) for path in output_dir.glob("**/regression_report.json")),
        key=lambda row: row.run,
    )
    lines = [f"## {title}", ""]
    if not rows:
        return "\n".join((*lines, f"No regression reports were found under `{output_dir}`.", ""))

    lines.extend(
        (
            "| Run | Regression | Fixtures | Generated cases | Branch coverage |",
            "| --- | --- | ---: | --- | --- |",
        )
    )
    warnings: list[str] = []
    for row in rows:
        lines.append(
            f"| {_table(row.run)} | {row.regression} | {row.fixtures} | "
            f"{row.generated_cases} | {row.branch_coverage} |"
        )
        warnings.extend(f"`{row.run}`: {warning}" for warning in row.warnings)
    if warnings:
        lines.extend(("", "Warnings:", "", *(f"- {warning}" for warning in warnings)))
    return "\n".join((*lines, ""))


def _read_row(report_path: Path, output_dir: Path) -> SummaryRow:
    run = _path_run_name(report_path.parent, output_dir)
    try:
        payload = _read_object(report_path)
    except (OSError, ValueError) as error:
        return SummaryRow(
            run=run,
            regression="Unknown",
            fixtures="-",
            generated_cases="Not reported",
            branch_coverage="Not reported",
            warnings=(f"could not read `{report_path.name}`: {error}",),
        )

    fixtures = payload.get("fixtures")
    warnings: list[str] = []
    if isinstance(fixtures, list):
        fixture_count = str(len(fixtures))
        failed_count = sum(
            isinstance(fixture, dict) and fixture.get("passed") is False for fixture in fixtures
        )
    else:
        fixtures = []
        fixture_count = "-"
        failed_count = 0
        warnings.append("regression report has no `fixtures` list")

    passed = payload.get("passed")
    if passed is True:
        regression = "Passed"
    elif passed is False:
        fixture_label = "fixture" if failed_count == 1 else "fixtures"
        regression = f"Failed ({failed_count} {fixture_label})"
    else:
        regression = "Unknown"
        warnings.append("regression report has no boolean `passed` value")

    generated_cases, branch_coverage, coverage_warnings = _coverage_cells(report_path.parent)
    return SummaryRow(
        run=_reported_run_name(fixtures, fallback=run),
        regression=regression,
        fixtures=fixture_count,
        generated_cases=generated_cases,
        branch_coverage=branch_coverage,
        warnings=tuple((*warnings, *coverage_warnings)),
    )


def _coverage_cells(directory: Path) -> tuple[str, str, list[str]]:
    cases: list[str] = []
    branches: list[str] = []
    warnings: list[str] = []
    for path in sorted(directory.glob("*-coverage.json")):
        try:
            payload = _read_object(path)
            selected = _integer(payload, "selected_case_count")
            covered = _integer(payload, "covered_branch_count")
            expected = _integer(payload, "expected_branch_count")
            complete = payload.get("complete")
            if not isinstance(complete, bool):
                raise ValueError("expected boolean `complete`")
            name = _table(path.name.removesuffix("-coverage.json"))
            cases.append(f"{name}: {selected}")
            status = "complete" if complete else "incomplete"
            branches.append(f"{name}: {covered}/{expected} ({status})")
        except (OSError, ValueError) as error:
            warnings.append(f"could not read `{path.name}`: {error}")
    return "<br>".join(cases) or "Not reported", "<br>".join(branches) or "Not reported", warnings


def _reported_run_name(fixtures: list[object], *, fallback: str) -> str:
    if fallback != "default":
        return fallback
    for fixture in fixtures:
        if not isinstance(fixture, dict) or not isinstance(fixture.get("candidate"), dict):
            continue
        reference = fixture["candidate"].get("template_reference")
        if isinstance(reference, str) and ":" in reference:
            return f"v{reference.rsplit(':', 1)[-1]} (default)"
    return fallback


def _path_run_name(directory: Path, output_dir: Path) -> str:
    relative = directory.relative_to(output_dir)
    return relative.as_posix() if relative.parts else "default"


def _read_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON at line {error.lineno}") from error
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object")
    return payload


def _integer(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if type(value) is not int:
        raise ValueError(f"expected integer `{key}`")
    return value


def _table(value: str) -> str:
    return value.replace("|", "\\|")


def _environment_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value else None


if __name__ == "__main__":
    main()
