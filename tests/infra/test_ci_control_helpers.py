"""Tests for CI helper scripts used by downstream translation repositories."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


def test_validate_translation_config_accepts_existing_upstream_tags(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """A valid translation control config should verify concrete upstream tags."""

    upstream = _build_tagged_remote(tmp_path, ("v1.29.1", "v1.30.0"))
    config = _write_translation_config(
        tmp_path / "translation-config.yml",
        upstream=upstream,
        supported_versions=("v1.29.1", "v1.30.0"),
    )
    summary = tmp_path / "summary.md"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "validate_translation_config.py"),
            "--config",
            str(config),
            "--summary",
            str(summary),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All configured upstream tags exist" in result.stdout
    assert summary.is_file()
    assert "Supported versions: `v1.29.1, v1.30.0`" in summary.read_text(
        encoding="utf-8",
    )


def test_validate_translation_config_rejects_missing_upstream_tags(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Missing upstream tags should fail before version branches are changed."""

    upstream = _build_tagged_remote(tmp_path, ("v1.29.1",))
    config = _write_translation_config(
        tmp_path / "translation-config.yml",
        upstream=upstream,
        supported_versions=("v1.29.1", "v1.30.0"),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "validate_translation_config.py"),
            "--config",
            str(config),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Missing upstream tags: v1.30.0" in result.stderr


def test_download_clean_scaffold_artifacts_uses_latest_successful_tooling_run(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The artifact downloader should centralize gh run lookup/download behavior."""

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

args = sys.argv[1:]
if args[:2] == ["run", "list"]:
    print("12345")
    raise SystemExit(0)
if args[:2] == ["run", "download"]:
    name = args[args.index("--name") + 1]
    output_dir = Path(args[args.index("--dir") + 1])
    marker = output_dir / "upstream-workspaces" / "dsw-science-europe" / name
    marker.mkdir(parents=True, exist_ok=True)
    (marker / "artifact.txt").write_text(name + "\\n", encoding="utf-8")
    raise SystemExit(0)
raise SystemExit(f"unexpected gh args: {args}")
""",
        encoding="utf-8",
    )
    fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

    output_dir = tmp_path / "tooling-artifacts"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "download_clean_scaffold_artifacts.py"),
            "--repo",
            "owner/tool",
            "--workflow",
            "ci.yml",
            "--output-dir",
            str(output_dir),
            "--artifact",
            "artifact-a",
            "--artifact",
            "artifact-b",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "owner/tool run 12345" in result.stdout
    assert (output_dir / "upstream-workspaces/dsw-science-europe/artifact-a").is_dir()
    assert (output_dir / "upstream-workspaces/dsw-science-europe/artifact-b").is_dir()


def test_resolve_migration_source_prefers_manual_input(repo_root: Path, tmp_path: Path) -> None:
    """Manual workflow dispatch input should be the migration source."""

    output = tmp_path / "github-output.txt"
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_migration_source.py"),
            "--event-name",
            "workflow_dispatch",
            "--manual-source-version",
            "v1.30.0",
            "--previous-latest-version",
            "v1.29.1",
            "--current-latest-version",
            "v1.30.1",
            "--github-output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Using migration source version: v1.30.0" in result.stdout
    assert output.read_text(encoding="utf-8").splitlines() == [
        "skip=false",
        "source_version=v1.30.0",
    ]


def test_resolve_migration_source_skips_non_translation_workflow_run(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Non-version workflow_run branches should not trigger migration fan-out."""

    output = tmp_path / "github-output.txt"
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "resolve_migration_source.py"),
            "--event-name",
            "workflow_run",
            "--workflow-run-head-branch",
            "feature/readme",
            "--previous-latest-version",
            "v1.29.1",
            "--current-latest-version",
            "v1.30.1",
            "--github-output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "skipping" in result.stdout
    assert output.read_text(encoding="utf-8").splitlines() == ["skip=true"]


def _build_tagged_remote(tmp_path: Path, tags: tuple[str, ...]) -> str:
    remote = tmp_path / "upstream-template"
    remote.mkdir()
    _git(remote, "init", "--initial-branch=main")
    _git(remote, "config", "user.name", "Test Bot")
    _git(remote, "config", "user.email", "test@example.com")
    for tag in tags:
        (remote / "template.json").write_text(f'{{"version":"{tag[1:]}"}}\n', encoding="utf-8")
        _git(remote, "add", "template.json")
        _git(remote, "commit", "-m", f"template {tag}")
        _git(remote, "tag", tag)
    return str(remote)


def _write_translation_config(
    path: Path,
    *,
    upstream: str,
    supported_versions: tuple[str, ...],
) -> Path:
    supported_versions_yaml = "\n".join(f"    - {version}" for version in supported_versions)
    path.write_text(
        f"""
schema_version: 1

template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: {upstream}
  supported_ref_spec: v1.29.1+
  supported_versions:
{supported_versions_yaml}

translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant
  translated_template_organization_id: dsw
  translated_template_id: science-europe-zh-hant
  translated_template_name: Science Europe DMP Template (zh-Hant)

branches:
  version_branch_prefix: translation/

tooling:
  repository: ThreeMonth03/DSW-document-template-tool
  ref: master

migration:
  mode: exact-only
  non_exact_policy: leave_empty_needs_translation
  auto_pr_enabled: true
  auto_pr_branch_prefix: automation/migrate
  auto_merge_when_clean: true

publish:
  enabled: false
  target_repository: depositar/science-europe-template-zh_Hant
  branch_prefix: sync/
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
