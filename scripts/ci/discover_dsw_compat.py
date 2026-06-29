#!/usr/bin/env python3
"""Discover upstream template metamodels and verify DSW runtime coverage."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "src"))

from resolve_upstream_refs import resolve_refs  # noqa: E402

from dsw_document_template_tool.dsw_compat import (  # noqa: E402
    OFFICIAL_TEMPLATE_METAMODEL_SPEC_URL,
    DswCompatSourceError,
    DswTemplateMetamodelSupport,
    fetch_official_template_metamodel_support,
    runtime_candidate_message,
)
from dsw_document_template_tool.translation_migration import (  # noqa: E402
    DswPreviewRuntime,
    TranslationMigrationError,
    load_preview_runtimes,
    preview_runtime_for_template,
)


@dataclass(frozen=True)
class TemplateRefMetadata:
    """Minimal upstream template metadata needed for compatibility checks."""

    requested_ref: str
    resolved_ref: str
    version: str
    metamodel_version: str
    runtime: DswPreviewRuntime | None
    error: str | None = None


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="discover upstream template metamodels and DSW runtime coverage",
    )
    parser.add_argument("--remote", required=True, help="Upstream template git remote.")
    parser.add_argument(
        "--compat",
        type=Path,
        default=REPO_ROOT / "config" / "dsw-compat.yml",
        help="DSW compatibility config file.",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".cache/upstream-compat-discovery"),
        help="Git cache directory for upstream metadata discovery.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        help="Optional GitHub step summary file to append a Markdown report to.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional Markdown report file to write for follow-up automation.",
    )
    parser.add_argument(
        "--metamodel-source-url",
        default=OFFICIAL_TEMPLATE_METAMODEL_SPEC_URL,
        help=(
            "Official DSW document-template metamodel source used to suggest "
            "candidate runtimes for unsupported metamodels."
        ),
    )
    parser.add_argument(
        "--no-runtime-suggestions",
        action="store_true",
        help="Do not fetch official metamodel mapping suggestions.",
    )
    parser.add_argument("refs", nargs="+", help="Refs to scan, e.g. latest main v1.29.1+")
    args = parser.parse_args()

    try:
        runtimes = load_preview_runtimes(args.compat)
        resolved_refs = resolve_refs(remote=args.remote, refs=args.refs)
        prepare_cache(args.cache, args.remote)
        results = [
            inspect_ref(args.cache, requested_ref=ref, runtimes=runtimes) for ref in resolved_refs
        ]
        failures = [result for result in results if result.error is not None]
        support_by_metamodel: dict[str, DswTemplateMetamodelSupport] | None = None
        support_error: str | None = None
        if failures and not args.no_runtime_suggestions:
            try:
                support_by_metamodel = fetch_official_template_metamodel_support(
                    args.metamodel_source_url,
                )
            except DswCompatSourceError as exc:
                support_error = str(exc)

        report = render_markdown_report(
            results,
            compat_path=args.compat,
            metamodel_source_url=args.metamodel_source_url,
            support_by_metamodel=support_by_metamodel,
            support_error=support_error,
        )
        print(report)
        summary_path = args.summary or env_path("GITHUB_STEP_SUMMARY")
        report_path = args.report or env_path("UPSTREAM_TEMPLATE_DISCOVERY_REPORT")
        if summary_path is not None:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            with summary_path.open("a", encoding="utf-8") as summary_file:
                summary_file.write(report)
                summary_file.write("\n")
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report + "\n", encoding="utf-8")

        if failures:
            raise SystemExit(1)
    except (OSError, subprocess.CalledProcessError, TranslationMigrationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def prepare_cache(cache_dir: Path, remote: str) -> None:
    """Create or refresh a local upstream git cache."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    if not (cache_dir / ".git").is_dir():
        run_git(cache_dir, "init")
        run_git(cache_dir, "remote", "add", "origin", remote)
    else:
        run_git(cache_dir, "remote", "set-url", "origin", remote)
    run_git(
        cache_dir,
        "fetch",
        "--prune",
        "--tags",
        "origin",
        "+refs/heads/*:refs/remotes/origin/*",
    )


def env_path(name: str) -> Path | None:
    """Return a non-empty environment variable as a path."""

    value = os.environ.get(name, "").strip()
    return Path(value) if value else None


def inspect_ref(
    repo_dir: Path,
    *,
    requested_ref: str,
    runtimes: tuple[DswPreviewRuntime, ...],
) -> TemplateRefMetadata:
    """Inspect one upstream ref and return its runtime coverage result."""

    resolved_ref = resolve_checkout_ref(repo_dir, requested_ref)
    payload = json.loads(git_stdout(repo_dir, "show", f"{resolved_ref}:template.json"))
    version = f"v{payload['version']}"
    metamodel_version = str(payload.get("metamodelVersion", ""))
    try:
        runtime = preview_runtime_for_template_from(runtimes, version, metamodel_version)
    except TranslationMigrationError as exc:
        return TemplateRefMetadata(
            requested_ref=requested_ref,
            resolved_ref=resolved_ref,
            version=version,
            metamodel_version=metamodel_version,
            runtime=None,
            error=str(exc),
        )
    return TemplateRefMetadata(
        requested_ref=requested_ref,
        resolved_ref=resolved_ref,
        version=version,
        metamodel_version=metamodel_version,
        runtime=runtime,
    )


def preview_runtime_for_template_from(
    runtimes: tuple[DswPreviewRuntime, ...],
    version: str,
    metamodel_version: str,
) -> DswPreviewRuntime:
    """Like preview_runtime_for_template, but scoped to a provided runtime set."""

    # The public helper reads the default config. Keep this tiny adapter so tests
    # can point discovery at a temporary compatibility table.
    if runtimes == load_preview_runtimes():
        return preview_runtime_for_template(version, metamodel_version)
    for runtime in runtimes:
        if version_in_runtime(version, runtime):
            if runtime.metamodel_version != metamodel_version:
                raise TranslationMigrationError(
                    f"Template {version} uses metamodelVersion {metamodel_version!r}, "
                    f"but configured runtime {runtime.metamodel_key!r} expects "
                    f"{runtime.metamodel_version!r}"
                )
            return runtime
    raise TranslationMigrationError(
        f"No DSW preview runtime configured for template {version} "
        f"with metamodelVersion {metamodel_version!r}"
    )


def version_in_runtime(version: str, runtime: DswPreviewRuntime) -> bool:
    """Return whether a semantic version tag is covered by a runtime range."""

    from dsw_document_template_tool.translation_migration import version_sort_key

    version_key = version_sort_key(version)
    if version_key < version_sort_key(runtime.min_version):
        return False
    return runtime.max_version is None or version_key <= version_sort_key(runtime.max_version)


def resolve_checkout_ref(repo_dir: Path, requested_ref: str) -> str:
    """Resolve latest/tags/branches to a git object usable by git-show."""

    if requested_ref == "latest":
        latest_tag = git_stdout(repo_dir, "tag", "-l", "v*").splitlines()
        version_tags = [
            tag
            for tag in latest_tag
            if tag.startswith("v") and all(part.isdigit() for part in tag[1:].split("."))
        ]
        if not version_tags:
            raise ValueError("Could not resolve latest: upstream has no version tags")
        from dsw_document_template_tool.translation_migration import sorted_versions

        return sorted_versions(version_tags)[-1]
    if git_check(repo_dir, "rev-parse", "--verify", "--quiet", requested_ref):
        return requested_ref
    branch_ref = f"origin/{requested_ref}"
    if git_check(repo_dir, "rev-parse", "--verify", "--quiet", branch_ref):
        return branch_ref
    raise ValueError(f"Could not resolve upstream ref {requested_ref!r}")


def render_markdown_report(
    results: list[TemplateRefMetadata],
    *,
    compat_path: Path,
    metamodel_source_url: str = OFFICIAL_TEMPLATE_METAMODEL_SPEC_URL,
    support_by_metamodel: dict[str, DswTemplateMetamodelSupport] | None = None,
    support_error: str | None = None,
) -> str:
    """Render a concise Markdown compatibility report."""

    lines = [
        "## DSW Compatibility Discovery",
        "",
        f"Compatibility table: `{compat_path.as_posix()}`",
        "",
        "| Ref | Version | metamodelVersion | Runtime | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        if result.runtime is None:
            runtime = "-"
            status = f"unsupported: {result.error}"
        else:
            runtime = (
                f"{result.runtime.metamodel_key} / DSW {result.runtime.dsw_version} / "
                f"TDK {result.runtime.tdk_version}"
            )
            status = "covered"
        lines.append(
            "| "
            f"`{result.requested_ref}` | `{result.version}` | "
            f"`{result.metamodel_version}` | {runtime} | {status} |"
        )

    unsupported = [result for result in results if result.error is not None]
    if unsupported:
        lines.extend(
            [
                "",
                "### Unsupported Metamodels",
                "",
                "CI found upstream template refs that are not covered by "
                "`config/dsw-compat.yml`. Add a runtime only after smoke-testing a "
                "matching DSW server and dsw-tdk version.",
                "",
                f"Official metamodel source: {metamodel_source_url}",
                "",
            ]
        )
        if support_error:
            lines.extend([f"Runtime suggestion source unavailable: {support_error}", ""])
        for result in unsupported:
            lines.append(
                f"- `{result.version}` (`{result.requested_ref}`) uses "
                f"`metamodelVersion={result.metamodel_version}`: {result.error}"
            )
            lines.append(
                f"  - {runtime_candidate_message(result.metamodel_version, support_by_metamodel)}"
            )
    return "\n".join(lines)


def run_git(repo_dir: Path, *args: str) -> None:
    """Run a git command in ``repo_dir``."""

    subprocess.run(["git", "-C", str(repo_dir), *args], check=True)


def git_stdout(repo_dir: Path, *args: str) -> str:
    """Run git and return stdout."""

    return subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout


def git_check(repo_dir: Path, *args: str) -> bool:
    """Return whether a git command succeeds."""

    return (
        subprocess.run(
            ["git", "-C", str(repo_dir), *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


if __name__ == "__main__":
    main()
