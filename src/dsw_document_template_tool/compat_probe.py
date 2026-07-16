"""Plan and render optimistic DSW metamodel compatibility probes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .translation_repository import (
    DswPreviewRuntime,
    TranslationRepositoryError,
    load_preview_runtimes_text,
    version_sort_key,
)
from .yaml_config import YamlConfigError, load_yaml_text

EVIDENCE_ASSIGNMENTS_START = "  # BEGIN GENERATED RUNTIME KNOWLEDGE MODEL ASSIGNMENTS"
EVIDENCE_ASSIGNMENTS_END = "  # END GENERATED RUNTIME KNOWLEDGE MODEL ASSIGNMENTS"
DISCOVERY_ROW_PATTERN = re.compile(
    r"^\|\s*`(?P<ref>[^`]+)`\s*"
    r"\|\s*`(?P<version>[^`]+)`\s*"
    r"\|\s*`(?P<metamodel>[^`]+)`\s*"
    r"\|\s*(?P<runtime>.*?)\s*"
    r"\|\s*(?P<status>.*?)\s*\|$"
)


@dataclass(frozen=True)
class DiscoveryRow:
    """One row from the upstream compatibility discovery report."""

    ref: str
    version: str
    metamodel_version: str
    status: str


@dataclass(frozen=True)
class ProbeChange:
    """A generated optimistic runtime probe change."""

    metamodel_version: str
    min_version: str
    previous_metamodel_version: str
    dsw_version: str
    tdk_version: str
    knowledge_model_fixture: str


@dataclass(frozen=True)
class ProbePlan:
    """Rendered compatibility probe output."""

    runtimes: tuple[DswPreviewRuntime, ...]
    runtime_knowledge_models: tuple[tuple[str, str], ...]
    changes: tuple[ProbeChange, ...]


def build_probe_plan(*, report: str, compat_text: str, evidence_text: str) -> ProbePlan:
    """Return a compatibility table with optimistic probe rows added."""

    discovery_rows = parse_discovery_rows(report)
    try:
        runtimes = list(
            load_preview_runtimes_text(
                compat_text,
                source="compatibility config",
            )
        )
    except TranslationRepositoryError as exc:
        raise SystemExit(str(exc)) from exc
    runtime_knowledge_models = load_runtime_knowledge_models(evidence_text)
    validate_evidence_assignments(runtimes, runtime_knowledge_models)
    unsupported = [row for row in discovery_rows if row.status.startswith("unsupported")]
    if not unsupported:
        return ProbePlan(
            runtimes=tuple(runtimes),
            runtime_knowledge_models=ordered_evidence_assignments(
                runtimes,
                runtime_knowledge_models,
            ),
            changes=(),
        )

    unsupported_by_metamodel: dict[str, list[DiscoveryRow]] = {}
    for row in unsupported:
        unsupported_by_metamodel.setdefault(row.metamodel_version, []).append(row)

    updated_runtimes = list(runtimes)
    changes: list[ProbeChange] = []
    for metamodel_version, rows in sorted(
        unsupported_by_metamodel.items(),
        key=lambda item: version_sort_key(min(row.version for row in item[1])),
    ):
        first_unsupported = sorted(rows, key=lambda row: version_sort_key(row.version))[0]
        previous = previous_runtime_for_version(updated_runtimes, first_unsupported.version)
        candidate = next(
            (
                runtime
                for runtime in updated_runtimes
                if runtime.metamodel_version == metamodel_version
            ),
            None,
        )
        if candidate is None:
            knowledge_model_fixture = runtime_knowledge_models[previous.metamodel_key]
            range_end = latest_discovered_version(
                discovery_rows,
                before_version=first_unsupported.version,
                metamodel_version=previous.metamodel_version,
            )
            previous_index = updated_runtimes.index(previous)
            updated_runtimes[previous_index] = close_previous_runtime(
                previous,
                max_version=range_end,
                discovery_rows=discovery_rows,
            )
            candidate = DswPreviewRuntime(
                metamodel_key=metamodel_key_for(metamodel_version),
                metamodel_version=metamodel_version,
                dsw_version=previous.dsw_version,
                tdk_version=previous.tdk_version,
                min_version=first_unsupported.version,
                max_version=None,
                upstream_template_artifact_refs=f"{first_unsupported.version}+",
            )
            updated_runtimes.insert(previous_index + 1, candidate)
            runtime_knowledge_models[candidate.metamodel_key] = knowledge_model_fixture
        else:
            knowledge_model_fixture = runtime_knowledge_models[candidate.metamodel_key]
        changes.append(
            ProbeChange(
                metamodel_version=metamodel_version,
                min_version=first_unsupported.version,
                previous_metamodel_version=previous.metamodel_version,
                dsw_version=candidate.dsw_version,
                tdk_version=candidate.tdk_version,
                knowledge_model_fixture=knowledge_model_fixture,
            )
        )

    sorted_runtimes = tuple(
        sorted(updated_runtimes, key=lambda runtime: version_sort_key(runtime.min_version))
    )
    return ProbePlan(
        runtimes=sorted_runtimes,
        runtime_knowledge_models=ordered_evidence_assignments(
            sorted_runtimes,
            runtime_knowledge_models,
        ),
        changes=tuple(changes),
    )


def load_runtime_knowledge_models(evidence_text: str) -> dict[str, str]:
    """Load runtime-to-Knowledge-Model assignments from evidence YAML."""

    try:
        payload = load_yaml_text(evidence_text, source="regression evidence config")
    except YamlConfigError as exc:
        raise SystemExit(str(exc)) from exc
    if not isinstance(payload, dict):
        raise SystemExit("Regression evidence config must contain a mapping")
    raw_assignments = payload.get("runtime_knowledge_models")
    if not isinstance(raw_assignments, dict) or not raw_assignments:
        raise SystemExit(
            "Regression evidence config must define non-empty runtime_knowledge_models"
        )
    assignments: dict[str, str] = {}
    for key, value in raw_assignments.items():
        if not isinstance(key, str) or not key:
            raise SystemExit("Regression evidence runtime keys must be non-empty strings")
        if not isinstance(value, str) or not value:
            raise SystemExit(f"Regression evidence assignment {key!r} must be a non-empty string")
        assignments[key] = value
    return assignments


def validate_evidence_assignments(
    runtimes: list[DswPreviewRuntime] | tuple[DswPreviewRuntime, ...],
    assignments: dict[str, str],
) -> None:
    """Require an exact Knowledge Model assignment for every runtime row."""

    runtime_keys = {runtime.metamodel_key for runtime in runtimes}
    assignment_keys = set(assignments)
    if runtime_keys == assignment_keys:
        return
    missing = sorted(runtime_keys - assignment_keys)
    extra = sorted(assignment_keys - runtime_keys)
    details = []
    if missing:
        details.append(f"missing: {', '.join(missing)}")
    if extra:
        details.append(f"unknown: {', '.join(extra)}")
    raise SystemExit(
        "Regression evidence runtime assignments do not match DSW runtimes ("
        + "; ".join(details)
        + ")"
    )


def ordered_evidence_assignments(
    runtimes: list[DswPreviewRuntime] | tuple[DswPreviewRuntime, ...],
    assignments: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    """Return evidence assignments in runtime version order."""

    return tuple(
        (runtime.metamodel_key, assignments[runtime.metamodel_key]) for runtime in runtimes
    )


def parse_discovery_rows(report: str) -> list[DiscoveryRow]:
    """Parse the Markdown discovery table into structured rows."""

    rows: list[DiscoveryRow] = []
    for line in report.splitlines():
        match = DISCOVERY_ROW_PATTERN.match(line.strip())
        if match is None:
            continue
        rows.append(
            DiscoveryRow(
                ref=match.group("ref"),
                version=match.group("version"),
                metamodel_version=match.group("metamodel"),
                status=match.group("status").strip(),
            )
        )
    if not rows:
        raise SystemExit("Discovery report does not contain a parseable compatibility table")
    return rows


def previous_runtime_for_version(
    runtimes: list[DswPreviewRuntime],
    version: str,
) -> DswPreviewRuntime:
    """Return the closest configured runtime before ``version``."""

    candidates = [
        runtime
        for runtime in runtimes
        if version_sort_key(runtime.min_version) < version_sort_key(version)
    ]
    if not candidates:
        raise SystemExit(
            f"Cannot build compatibility probe before first configured version {version}"
        )
    return sorted(candidates, key=lambda runtime: version_sort_key(runtime.min_version))[-1]


def latest_discovered_version(
    rows: list[DiscoveryRow],
    *,
    before_version: str,
    metamodel_version: str,
) -> str:
    """Return the last discovered version for a previous metamodel.

    The previous metamodel might itself be a newly generated probe row, so the
    source discovery report may still mark it as unsupported. For range
    bookkeeping, the important fact is the upstream version/metamodel boundary;
    CI will decide whether each probe runtime actually works.
    """

    previous_versions = [
        row.version
        for row in rows
        if row.metamodel_version == metamodel_version
        and version_sort_key(row.version) < version_sort_key(before_version)
    ]
    if not previous_versions:
        raise SystemExit(
            "Cannot safely close the previous runtime range because discovery did not "
            f"include a version for metamodel {metamodel_version} before {before_version}"
        )
    return sorted(previous_versions, key=version_sort_key)[-1]


def close_previous_runtime(
    runtime: DswPreviewRuntime,
    *,
    max_version: str,
    discovery_rows: list[DiscoveryRow],
) -> DswPreviewRuntime:
    """Close a runtime range before handing later versions to a probe row."""

    if runtime.max_version is not None and version_sort_key(
        runtime.max_version
    ) >= version_sort_key(max_version):
        return runtime
    covered_refs = [
        row.version
        for row in discovery_rows
        if row.status == "covered"
        and row.metamodel_version == runtime.metamodel_version
        and version_sort_key(runtime.min_version)
        <= version_sort_key(row.version)
        <= version_sort_key(max_version)
    ]
    artifact_refs = " ".join(sorted(covered_refs, key=version_sort_key))
    return DswPreviewRuntime(
        metamodel_key=runtime.metamodel_key,
        metamodel_version=runtime.metamodel_version,
        dsw_version=runtime.dsw_version,
        tdk_version=runtime.tdk_version,
        min_version=runtime.min_version,
        max_version=max_version,
        upstream_template_artifact_refs=artifact_refs or runtime.upstream_template_artifact_refs,
    )


def metamodel_key_for(metamodel_version: str) -> str:
    """Return the conventional runtime key for a metamodel version."""

    return metamodel_version.replace(".", "-")


def render_compat_config(runtimes: tuple[DswPreviewRuntime, ...]) -> str:
    """Render the DSW compatibility config in stable, reviewable YAML."""

    lines = [
        "schema_version: 1",
        "",
        "# DSW server / TDK runtimes that are proven by CI to render upstream",
        "# Science Europe template metamodels. Keep this file as the single source",
        "# of truth; workflow matrices and downstream version-branch workflows are",
        "# expected to stay in sync with it.",
        "runtimes:",
    ]
    for runtime in runtimes:
        lines.extend(
            [
                f'  - metamodel_key: "{runtime.metamodel_key}"',
                f'    metamodel_version: "{runtime.metamodel_version}"',
                f'    dsw_version: "{runtime.dsw_version}"',
                f'    tdk_version: "{runtime.tdk_version}"',
                f'    min_version: "{runtime.min_version}"',
                f"    max_version: {render_yaml_nullable_string(runtime.max_version)}",
                f'    upstream_template_artifact_refs: "{runtime.upstream_template_artifact_refs}"',
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_evidence_config(
    evidence_text: str,
    assignments: tuple[tuple[str, str], ...],
) -> str:
    """Replace only the generated runtime assignment block in evidence YAML."""

    lines = evidence_text.splitlines()
    try:
        start_index = lines.index(EVIDENCE_ASSIGNMENTS_START)
        end_index = lines.index(EVIDENCE_ASSIGNMENTS_END)
    except ValueError as exc:
        raise SystemExit(
            "Regression evidence config is missing generated assignment markers"
        ) from exc
    if end_index <= start_index:
        raise SystemExit("Regression evidence assignment markers are out of order")
    generated = [f'  "{key}": {fixture}' for key, fixture in assignments]
    rendered = [
        *lines[: start_index + 1],
        *generated,
        *lines[end_index:],
    ]
    return "\n".join(rendered).rstrip() + "\n"


def render_yaml_nullable_string(value: str | None) -> str:
    """Render a nullable string value."""

    return "null" if value is None else f'"{value}"'


def render_probe_report(report: str, *, plan: ProbePlan) -> str:
    """Render a committed compatibility probe report."""

    return (
        "# DSW Metamodel Compatibility Probe\n\n"
        "The scheduled upstream compatibility check found a Science Europe template "
        "version whose `metamodelVersion` is not covered by `config/dsw-compat.yml`.\n\n"
        "This file is generated by CI together with an optimistic runtime probe in "
        "`config/dsw-compat.yml`. A new probe is seeded from the closest previous "
        "DSW/TDK runtime and its pinned Knowledge Model fixture assignment. Later "
        "runs preserve reviewed candidate edits and let CI prove whether the API, "
        "import, packaging, coverage, and preview paths behave correctly.\n\n"
        f"{render_probe_changes(plan)}\n\n"
        "## Discovery Report\n\n"
        f"{report}\n\n"
        "## Maintainer Checklist\n\n"
        "- [ ] Confirm the probe row reuses the intended previous DSW/TDK runtime.\n"
        "- [ ] Confirm `config/regression-evidence.yml` reuses an appropriate pinned "
        "Knowledge Model fixture for the new runtime.\n"
        "- [ ] Review CI logs for Knowledge Model import, template package/import, "
        "preview render, and PDF render.\n"
        "- [ ] Download the clean scaffold artifacts and inspect the preview output.\n"
        "- [ ] If CI fails, replace the copied runtime with a newer DSW/TDK pair or "
        "patch the compatibility layer.\n"
        "- [ ] Run `make sync-dsw-runtime-matrix`.\n"
        "- [ ] Confirm clean scaffold release assets are produced for the new tag.\n"
    )


def render_probe_changes(plan: ProbePlan) -> str:
    """Render the generated probe row summary."""

    if not plan.changes:
        return (
            "## Probe Runtime Changes\n\n"
            "No new runtime row was generated because every unsupported metamodel in "
            "the report is already present in `config/dsw-compat.yml`."
        )
    lines = ["## Probe Runtime Changes", ""]
    for change in plan.changes:
        lines.append(
            "- "
            f"`metamodelVersion={change.metamodel_version}` from `{change.min_version}+` "
            f"uses candidate DSW `{change.dsw_version}` / TDK `{change.tdk_version}` "
            f"and KM fixture `{change.knowledge_model_fixture}`. The candidate was "
            f"initially derived from metamodel `{change.previous_metamodel_version}`; "
            "CI and maintainer review must prove or reject it."
        )
    return "\n".join(lines)


def render_pr_body(report_path: Path, *, plan: ProbePlan) -> str:
    """Render the pull request body."""

    return (
        "CI detected at least one upstream Science Europe template tag whose "
        "`metamodelVersion` is not covered by the checked-in DSW runtime matrix.\n\n"
        "This PR optimistically updates `config/dsw-compat.yml` and the generated "
        "runtime assignment block in `config/regression-evidence.yml`. A new probe is "
        "seeded from the closest previous DSW/TDK runtime and pinned KM fixture; "
        "later runs preserve reviewed candidate edits. CI is the first judge: if "
        "import, packaging, complete coverage, preview, and release checks stay "
        "green, a maintainer can inspect the artifacts and merge the runtime update.\n\n"
        f"The full discovery report and checklist are in `{report_path.as_posix()}`.\n\n"
        f"{render_probe_changes(plan)}\n\n"
        "Do not enable auto-merge for this PR. Unknown metamodel support still needs "
        "human review even when CI passes."
    )


def default_branch_for_plan(plan: ProbePlan) -> str:
    """Return the default automation branch for a probe plan."""

    if not plan.changes:
        return "automation/dsw-compat-probe"
    metamodels = "-".join(change.metamodel_version.replace(".", "-") for change in plan.changes)
    return f"automation/dsw-compat-probe-{metamodels}"


def default_title_for_plan(plan: ProbePlan) -> str:
    """Return the default pull request title for a probe plan."""

    if not plan.changes:
        return "Probe DSW document-template metamodel compatibility"
    metamodels = ", ".join(change.metamodel_version for change in plan.changes)
    return f"Probe DSW document-template metamodel {metamodels} compatibility"
