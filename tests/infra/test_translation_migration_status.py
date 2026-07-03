"""Tests for translation migration status reporting."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def test_status_output_detects_pending_migrations(repo_root: Path) -> None:
    """Changed dry-run output should be reported as pending migration work."""

    module = _load_status_module(repo_root)

    assert module.is_pending_output(
        "INFO: [v1.30.1 -> v1.30.0] changed paths:\n"
        "INFO: [v1.30.1 -> v1.30.0] dry run; not committing.\n"
    )
    assert not module.is_pending_output(
        "INFO: [v1.30.1 -> v1.30.0] no source translations were migrated; skipping PR.\n"
    )


def test_status_wrapper_uses_existing_migration_helper(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The status helper should wrap migration dry-runs instead of reimplementing them."""

    module = _load_status_module(repo_root)
    repo = _write_translation_config(tmp_path)
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    commands: list[list[str]] = []

    def fake_run(
        args: list[str],
        *,
        cwd: Path,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(args)
        assert cwd == repo_root
        assert capture_output
        assert text
        assert not check
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=(
                "INFO: [v1.30.1 -> v1.30.0] changed paths:\n"
                "INFO: [v1.30.1 -> v1.30.0] dry run; not committing.\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    status = module.check_source_version(
        repo=repo,
        tooling_root=repo_root,
        source_version="v1.30.1",
        target_version_args=["v1.30.0"],
        clean_artifact_root=artifact_root,
        tdk_executable="/tmp/dsw-tdk",
        verbose=False,
    )

    assert status.pending
    assert not status.error
    assert status.target_versions == ["v1.30.0"]
    assert commands == [
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "create_translation_migration_prs.py"),
            "--repo",
            str(repo),
            "--tooling-root",
            str(repo_root),
            "--source-version",
            "v1.30.1",
            "--dry-run",
            "--target-version",
            "v1.30.0",
            "--clean-artifact-root",
            str(artifact_root),
            "--tdk-executable",
            "/tmp/dsw-tdk",
        ]
    ]


def test_default_sources_are_auto_refresh_versions(repo_root: Path, tmp_path: Path) -> None:
    """Status checks should default to actively refreshed translation branches."""

    module = _load_status_module(repo_root)
    repo = _write_translation_config(tmp_path)
    config = module.load_translation_repository_config(repo / "translation-config.yml")

    assert module.default_source_versions(config) == ["v1.30.1"]


def _load_status_module(repo_root: Path) -> ModuleType:
    module_path = repo_root / "scripts" / "ci" / "check_translation_migration_status.py"
    spec = importlib.util.spec_from_file_location("check_translation_migration_status", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_translation_config(tmp_path: Path) -> Path:
    repo = tmp_path / "translation-repo"
    repo.mkdir()
    (repo / "translation-config.yml").write_text(
        """
schema_version: 1
template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: https://github.com/ds-wizard/science-europe-template.git
  supported_ref_spec: v1.30.0+
  supported_versions:
    - v1.30.0
    - v1.30.1
version_policy:
  defaults:
    state: available
    refresh: false
    migrate_into: false
    publish_release: false
    reason: scaffold only
  overrides:
    v1.30.0:
      state: maintenance
      refresh: manual
      migrate_into: auto
      publish_release: true
      reason: reviewed target
    v1.30.1:
      state: active
      refresh: auto
      migrate_into: auto
      publish_release: true
      reason: active source
translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant
  translated_template_organization_id: dsw
  translated_template_id: science-europe-zh-hant
  translated_template_name: Science Europe DMP Template (zh-Hant)
branches:
  control_branch: master
  version_branch_prefix: translation/
tooling:
  repository: owner/tool
  ref: master
migration:
  mode: exact-only
  non_exact_policy: leave_empty_needs_translation
  auto_pr_enabled: true
  auto_pr_branch_prefix: automation/migrate
  auto_merge_when_clean: true
publish:
  enabled: false
  target_repository: owner/publish
  branch_prefix: sync/
""".lstrip(),
        encoding="utf-8",
    )
    return repo
