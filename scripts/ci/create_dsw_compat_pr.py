#!/usr/bin/env python3
"""Open a compatibility probe PR for unsupported upstream DSW metamodels."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_COMPAT_PATH = Path("config/dsw-compat.yml")
DEFAULT_REPORT_PATH = Path("docs/compatibility/dsw-compatibility-probe.md")
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
class RuntimeRow:
    """One row from ``config/dsw-compat.yml``."""

    metamodel_key: str
    metamodel_version: str
    dsw_version: str
    tdk_version: str
    min_version: str
    max_version: str | None
    upstream_template_artifact_refs: str
    run_preview_regression: bool
    strict_project_preview: bool


@dataclass(frozen=True)
class ProbeChange:
    """A generated optimistic runtime probe change."""

    metamodel_version: str
    min_version: str
    previous_metamodel_version: str
    previous_dsw_version: str
    previous_tdk_version: str


@dataclass(frozen=True)
class ProbePlan:
    """Rendered compatibility probe output."""

    runtimes: tuple[RuntimeRow, ...]
    changes: tuple[ProbeChange, ...]


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="create or update a DSW compatibility probe pull request",
    )
    parser.add_argument("--report", type=Path, required=True, help="Discovery report file.")
    parser.add_argument(
        "--compat",
        type=Path,
        default=DEFAULT_COMPAT_PATH,
        help="DSW compatibility config file to update with probe runtimes.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to commit the report to.",
    )
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub repository, for example owner/name.",
    )
    parser.add_argument(
        "--base",
        default=os.environ.get("GITHUB_REF_NAME", "master"),
        help="Base branch for the probe PR.",
    )
    parser.add_argument(
        "--branch",
        default="",
        help="Branch to push the probe changes to. Defaults to a metamodel-specific name.",
    )
    parser.add_argument("--title", default="", help="Pull request title.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the report locally but do not commit, push, or create a PR.",
    )
    args = parser.parse_args()

    if not args.repository:
        raise SystemExit("--repository is required when GITHUB_REPOSITORY is not set")
    if not args.report.is_file():
        raise SystemExit(f"Report file does not exist: {args.report}")
    if not args.compat.is_file():
        raise SystemExit(f"Compatibility config does not exist: {args.compat}")

    report = args.report.read_text(encoding="utf-8").strip()
    plan = build_probe_plan(report=report, compat_text=args.compat.read_text(encoding="utf-8"))
    rendered_report = render_probe_report(report, plan=plan)
    branch = args.branch or default_branch_for_plan(plan)
    title = args.title or default_title_for_plan(plan)

    if args.dry_run:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(rendered_report, encoding="utf-8")
        print(f"INFO: wrote {args.report_path} (dry run)")
        return

    branch_existed = checkout_start_ref(branch=branch, base=args.base)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(rendered_report, encoding="utf-8")
    args.compat.write_text(render_compat_config(plan.runtimes), encoding="utf-8")

    run(["git", "add", str(args.report_path), str(args.compat)])

    if not has_staged_changes():
        if branch_existed:
            print("INFO: Compatibility probe is unchanged; ensuring PR exists.")
            create_or_update_pr(
                repository=args.repository,
                branch=branch,
                base=args.base,
                title=title,
                body=render_pr_body(args.report_path, plan=plan),
            )
            return
        print("INFO: Compatibility probe is unchanged; no remote branch to update.")
        return

    configure_git_identity()
    run(["git", "commit", "-m", "ci: probe DSW metamodel compatibility"])
    run(["git", "push", "--force-with-lease", "origin", f"HEAD:refs/heads/{branch}"])
    create_or_update_pr(
        repository=args.repository,
        branch=branch,
        base=args.base,
        title=title,
        body=render_pr_body(args.report_path, plan=plan),
    )


def build_probe_plan(*, report: str, compat_text: str) -> ProbePlan:
    """Return a compatibility table with optimistic probe rows added."""

    discovery_rows = parse_discovery_rows(report)
    runtimes = load_runtime_rows(compat_text)
    unsupported = [row for row in discovery_rows if row.status.startswith("unsupported")]
    if not unsupported:
        return ProbePlan(runtimes=tuple(runtimes), changes=())

    existing_metamodels = {runtime.metamodel_version for runtime in runtimes}
    unsupported_by_metamodel: dict[str, list[DiscoveryRow]] = {}
    for row in unsupported:
        if row.metamodel_version not in existing_metamodels:
            unsupported_by_metamodel.setdefault(row.metamodel_version, []).append(row)

    updated_runtimes = list(runtimes)
    changes: list[ProbeChange] = []
    for metamodel_version, rows in sorted(
        unsupported_by_metamodel.items(),
        key=lambda item: version_sort_key(min(row.version for row in item[1])),
    ):
        first_unsupported = sorted(rows, key=lambda row: version_sort_key(row.version))[0]
        previous = previous_runtime_for_version(updated_runtimes, first_unsupported.version)
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
        updated_runtimes.insert(
            previous_index + 1,
            RuntimeRow(
                metamodel_key=metamodel_key_for(metamodel_version),
                metamodel_version=metamodel_version,
                dsw_version=previous.dsw_version,
                tdk_version=previous.tdk_version,
                min_version=first_unsupported.version,
                max_version=None,
                upstream_template_artifact_refs=f"{first_unsupported.version}+",
                run_preview_regression=previous.run_preview_regression,
                strict_project_preview=previous.strict_project_preview,
            ),
        )
        existing_metamodels.add(metamodel_version)
        changes.append(
            ProbeChange(
                metamodel_version=metamodel_version,
                min_version=first_unsupported.version,
                previous_metamodel_version=previous.metamodel_version,
                previous_dsw_version=previous.dsw_version,
                previous_tdk_version=previous.tdk_version,
            )
        )

    return ProbePlan(
        runtimes=tuple(
            sorted(updated_runtimes, key=lambda runtime: version_sort_key(runtime.min_version))
        ),
        changes=tuple(changes),
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


def load_runtime_rows(compat_text: str) -> list[RuntimeRow]:
    """Parse checked-in DSW runtime rows."""

    payload = yaml.safe_load(compat_text)
    if not isinstance(payload, dict):
        raise SystemExit("Compatibility config must contain a mapping")
    raw_runtimes = payload.get("runtimes")
    if not isinstance(raw_runtimes, list) or not raw_runtimes:
        raise SystemExit("Compatibility config must define non-empty runtimes")
    return [runtime_from_payload(item) for item in raw_runtimes]


def runtime_from_payload(payload: object) -> RuntimeRow:
    """Load one runtime row from YAML."""

    if not isinstance(payload, dict):
        raise SystemExit("Each DSW runtime row must be a mapping")
    max_version = payload.get("max_version")
    if max_version is not None and not isinstance(max_version, str):
        raise SystemExit("Runtime max_version must be a string or null")
    return RuntimeRow(
        metamodel_key=required_str(payload, "metamodel_key"),
        metamodel_version=required_str(payload, "metamodel_version"),
        dsw_version=required_str(payload, "dsw_version"),
        tdk_version=required_str(payload, "tdk_version"),
        min_version=required_str(payload, "min_version"),
        max_version=max_version,
        upstream_template_artifact_refs=required_str(payload, "upstream_template_artifact_refs"),
        run_preview_regression=bool(payload.get("run_preview_regression", False)),
        strict_project_preview=bool(payload.get("strict_project_preview", False)),
    )


def required_str(payload: dict[object, object], key: str) -> str:
    """Return a required string field from a runtime mapping."""

    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"Runtime field {key!r} must be a non-empty string")
    return value


def previous_runtime_for_version(runtimes: list[RuntimeRow], version: str) -> RuntimeRow:
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
    runtime: RuntimeRow,
    *,
    max_version: str,
    discovery_rows: list[DiscoveryRow],
) -> RuntimeRow:
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
    return RuntimeRow(
        metamodel_key=runtime.metamodel_key,
        metamodel_version=runtime.metamodel_version,
        dsw_version=runtime.dsw_version,
        tdk_version=runtime.tdk_version,
        min_version=runtime.min_version,
        max_version=max_version,
        upstream_template_artifact_refs=artifact_refs or runtime.upstream_template_artifact_refs,
        run_preview_regression=runtime.run_preview_regression,
        strict_project_preview=runtime.strict_project_preview,
    )


def metamodel_key_for(metamodel_version: str) -> str:
    """Return the conventional runtime key for a metamodel version."""

    return metamodel_version.replace(".", "-")


def version_sort_key(version: str) -> tuple[int, ...]:
    """Return a sortable numeric version key for tags such as ``v1.30.1``."""

    value = version.removeprefix("v")
    parts = value.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        raise SystemExit(f"Expected numeric version tag, got {version!r}")
    return tuple(int(part) for part in parts)


def render_compat_config(runtimes: tuple[RuntimeRow, ...]) -> str:
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
                f"    run_preview_regression: {render_yaml_bool(runtime.run_preview_regression)}",
                f"    strict_project_preview: {render_yaml_bool(runtime.strict_project_preview)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_yaml_nullable_string(value: str | None) -> str:
    """Render a nullable string value."""

    return "null" if value is None else f'"{value}"'


def render_yaml_bool(value: bool) -> str:
    """Render a YAML boolean."""

    return "true" if value else "false"


def render_probe_report(report: str, *, plan: ProbePlan) -> str:
    """Render a committed compatibility probe report."""

    return (
        "# DSW Metamodel Compatibility Probe\n\n"
        "The scheduled upstream compatibility check found a Science Europe template "
        "version whose `metamodelVersion` is not covered by `config/dsw-compat.yml`.\n\n"
        "This file is generated by CI together with an optimistic runtime probe in "
        "`config/dsw-compat.yml`. The probe reuses the closest previous DSW/TDK "
        "runtime and lets CI prove whether the API, import, packaging, and preview "
        "paths still behave the same way.\n\n"
        f"{render_probe_changes(plan)}\n\n"
        "## Discovery Report\n\n"
        f"{report}\n\n"
        "## Maintainer Checklist\n\n"
        "- [ ] Confirm the probe row reuses the intended previous DSW/TDK runtime.\n"
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
            f"reuses metamodel `{change.previous_metamodel_version}` runtime "
            f"DSW `{change.previous_dsw_version}` / TDK `{change.previous_tdk_version}` "
            "until CI and maintainer review prove or reject that assumption."
        )
    return "\n".join(lines)


def render_pr_body(report_path: Path, *, plan: ProbePlan) -> str:
    """Render the pull request body."""

    return (
        "CI detected at least one upstream Science Europe template tag whose "
        "`metamodelVersion` is not covered by the checked-in DSW runtime matrix.\n\n"
        "This PR optimistically updates `config/dsw-compat.yml` by copying the "
        "closest previous DSW/TDK runtime into a new probe row. CI is the first "
        "judge: if import, packaging, preview, and release checks stay green, a "
        "maintainer can review the artifacts and merge the runtime update.\n\n"
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


def configure_git_identity() -> None:
    """Configure a deterministic CI git identity when none is set."""

    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])


def checkout_start_ref(*, branch: str, base: str) -> bool:
    """Check out the automation start point without binding a local branch.

    The workflow pushes the generated commit with ``HEAD:refs/heads/<branch>``,
    so a local branch is unnecessary. Staying detached avoids failures when a
    maintainer already has the automation branch checked out in another
    worktree.
    """

    if remote_branch_exists(branch):
        run(["git", "fetch", "origin", f"refs/heads/{branch}:refs/remotes/origin/{branch}"])
        run(["git", "checkout", "--detach", f"origin/{branch}"])
        return True
    run(["git", "checkout", "--detach", fetch_base_ref(base)])
    return False


def fetch_base_ref(base: str) -> str:
    """Fetch and return the origin ref used to start a new automation branch."""

    origin_ref = f"origin/{base}"
    fetch_result = subprocess.run(
        ["git", "fetch", "origin", f"refs/heads/{base}:refs/remotes/{origin_ref}"],
        check=False,
    )
    if fetch_result.returncode != 0 or not git_ref_exists(origin_ref):
        raise SystemExit(
            f"Base branch origin/{base} does not exist or could not be fetched. "
            "Refusing to create a compatibility PR from the current checkout HEAD."
        )
    return origin_ref


def remote_branch_exists(branch: str) -> bool:
    """Return whether the remote automation branch already exists."""

    return (
        subprocess.run(
            ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def git_ref_exists(ref: str) -> bool:
    """Return whether a local git ref exists."""

    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def has_staged_changes() -> bool:
    """Return whether the index has staged changes."""

    return (
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            check=False,
        ).returncode
        != 0
    )


def create_or_update_pr(
    *,
    repository: str,
    branch: str,
    base: str,
    title: str,
    body: str,
) -> None:
    """Create or update the probe pull request."""

    body_file = Path(".cache/dsw-compat-pr-body.md")
    body_file.parent.mkdir(parents=True, exist_ok=True)
    body_file.write_text(body + "\n", encoding="utf-8")

    existing = subprocess.run(
        ["gh", "pr", "view", branch, "--repo", repository, "--json", "url", "--jq", ".url"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        run(
            [
                "gh",
                "pr",
                "edit",
                branch,
                "--repo",
                repository,
                "--title",
                title,
                "--body-file",
                str(body_file),
            ]
        )
        print(f"INFO: Updated existing PR: {existing.stdout.strip()}")
        return

    run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repository,
            "--base",
            base,
            "--head",
            branch,
            "--title",
            title,
            "--body-file",
            str(body_file),
        ]
    )


def run(args: list[str]) -> None:
    """Run a command."""

    subprocess.run(args, check=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
