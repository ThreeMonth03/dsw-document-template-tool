"""End-to-end tests for translation version-branch synchronization."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import yaml


def test_sync_translation_versions_creates_new_branch_from_clean_artifact(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A newly discovered clean artifact should initialize a matching branch."""

    sync_module = _load_sync_module(repo_root)
    origin = tmp_path / "origin.git"
    translation_repo = tmp_path / "translation-repo"
    artifact_root = tmp_path / "tooling-artifacts"

    _run_git(tmp_path, "init", "--bare", str(origin))
    _run_git(tmp_path, "init", "--initial-branch=master", str(translation_repo))
    _run_git(translation_repo, "config", "user.name", "Test User")
    _run_git(translation_repo, "config", "user.email", "test@example.invalid")
    _run_git(translation_repo, "remote", "add", "origin", str(origin))
    _write_translation_config(translation_repo / "translation-config.yml")
    (translation_repo / "README.md").write_text("translation control repo\n", encoding="utf-8")
    _run_git(translation_repo, "add", ".")
    _run_git(translation_repo, "commit", "-m", "initial control plane")
    _run_git(translation_repo, "push", "-u", "origin", "master")
    _run_git(translation_repo, "checkout", "-b", "translation/v1.30.1")
    _run_git(translation_repo, "commit", "--allow-empty", "-m", "initialize v1.30.1")
    _run_git(translation_repo, "push", "-u", "origin", "translation/v1.30.1")
    _run_git(translation_repo, "checkout", "master")

    _write_clean_artifact(artifact_root, version="v1.30.2")

    def fake_sync_blank_translation_output(
        *,
        checkout: Path,
        config,
        version: str,
        **_: object,
    ) -> None:
        paths = sync_module.version_paths(config, version)
        template_dir = checkout / paths.translated_template_dir
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "template.json").write_text(
            '{"id":"science-europe-zh-hant"}\n',
            encoding="utf-8",
        )
        package_path = checkout / paths.translated_template_package
        package_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.write_text("fake package\n", encoding="utf-8")

    monkeypatch.setattr(
        sync_module,
        "sync_blank_translation_output",
        fake_sync_blank_translation_output,
    )

    result = sync_module.sync_translation_versions(
        repo=translation_repo,
        tooling_root=repo_root,
        config_path=translation_repo / "translation-config.yml",
        clean_artifact_root=artifact_root,
        tdk_executable=Path(sys.executable).with_name("dsw-tdk"),
        push=False,
        dry_run=False,
    )

    assert result.previous_latest_version == "v1.30.1"
    assert result.current_latest_version == "v1.30.2"
    assert result.added_versions == ("v1.30.2",)
    assert result.created_branches == ("translation/v1.30.2",)
    assert result.config_changed is True

    config = yaml.safe_load(
        (translation_repo / "translation-config.yml").read_text(encoding="utf-8")
    )
    assert config["template"]["supported_versions"] == ["v1.30.1", "v1.30.2"]

    assert _git_show(translation_repo, "translation/v1.30.2:translation-config.yml")
    assert (
        _git_show(
            translation_repo,
            (
                "translation/v1.30.2:"
                "workspace/document-templates/compact/dsw-science-europe-1.30.2/"
                "artifact.txt"
            ),
        )
        == "compact v1.30.2\n"
    )
    assert (
        _git_show(
            translation_repo,
            (
                "translation/v1.30.2:"
                "outputs/document-templates/dsw-science-europe/v1.30.2/zh-Hant/"
                "dsw-science-europe-zh-hant-1.30.2.zip"
            ),
        )
        == "fake package\n"
    )


def test_sync_translation_versions_refreshes_existing_branch_from_clean_artifact(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """An existing version branch should be refreshable without dropping translations."""

    sync_module = _load_sync_module(repo_root)
    origin = tmp_path / "origin.git"
    translation_repo = tmp_path / "translation-repo"
    artifact_root = tmp_path / "tooling-artifacts"

    _run_git(tmp_path, "init", "--bare", str(origin))
    _run_git(tmp_path, "init", "--initial-branch=master", str(translation_repo))
    _run_git(translation_repo, "config", "user.name", "Test User")
    _run_git(translation_repo, "config", "user.email", "test@example.invalid")
    _run_git(translation_repo, "remote", "add", "origin", str(origin))
    _write_translation_config(translation_repo / "translation-config.yml")
    (translation_repo / "README.md").write_text("translation control repo\n", encoding="utf-8")
    _run_git(translation_repo, "add", ".")
    _run_git(translation_repo, "commit", "-m", "initial control plane")
    _run_git(translation_repo, "push", "-u", "origin", "master")

    _run_git(translation_repo, "checkout", "-b", "translation/v1.30.1")
    old_compact = (
        translation_repo
        / "workspace/document-templates/compact/dsw-science-europe-1.30.1/artifact.txt"
    )
    old_translation_marker = (
        translation_repo
        / "workspace/document-templates/translation/dsw-science-europe-1.30.1/translator.txt"
    )
    old_compact.parent.mkdir(parents=True, exist_ok=True)
    old_translation_marker.parent.mkdir(parents=True, exist_ok=True)
    old_compact.write_text("old compact\n", encoding="utf-8")
    old_translation_marker.write_text("manual translation\n", encoding="utf-8")
    _run_git(translation_repo, "add", ".")
    _run_git(translation_repo, "commit", "-m", "initialize v1.30.1")
    _run_git(translation_repo, "push", "-u", "origin", "translation/v1.30.1")
    _run_git(translation_repo, "checkout", "master")

    _write_clean_artifact(artifact_root, version="v1.30.1")

    def fake_merge_preserved_translations(
        *,
        checkout: Path,
        config,
        version: str,
        preserved_tree: Path,
        merged_tree: Path,
        **_: object,
    ) -> None:
        paths = sync_module.version_paths(config, version)
        shutil.copytree(checkout / paths.translation_tree_dir, merged_tree)
        preserved_marker = preserved_tree / "translator.txt"
        if preserved_marker.exists():
            shutil.copy2(preserved_marker, merged_tree / "translator.txt")
        sync_module.replace_tree(merged_tree, checkout / paths.translation_tree_dir)

    def fake_sync_blank_translation_output(
        *,
        checkout: Path,
        config,
        version: str,
        **_: object,
    ) -> None:
        paths = sync_module.version_paths(config, version)
        template_dir = checkout / paths.translated_template_dir
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "template.json").write_text(
            '{"id":"science-europe-zh-hant"}\n',
            encoding="utf-8",
        )
        package_path = checkout / paths.translated_template_package
        package_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.write_text("fake package\n", encoding="utf-8")

    monkeypatch.setattr(
        sync_module,
        "merge_preserved_translations",
        fake_merge_preserved_translations,
    )
    monkeypatch.setattr(
        sync_module,
        "sync_blank_translation_output",
        fake_sync_blank_translation_output,
    )

    result = sync_module.sync_translation_versions(
        repo=translation_repo,
        tooling_root=repo_root,
        config_path=translation_repo / "translation-config.yml",
        clean_artifact_root=artifact_root,
        tdk_executable=Path(sys.executable).with_name("dsw-tdk"),
        push=False,
        dry_run=False,
        refresh_existing=True,
    )

    assert result.previous_latest_version == "v1.30.1"
    assert result.current_latest_version == "v1.30.1"
    assert result.added_versions == ()
    assert result.created_branches == ()
    assert result.refreshed_branches == ("translation/v1.30.1",)
    assert result.config_changed is False
    assert (
        _git_show(
            translation_repo,
            (
                "translation/v1.30.1:"
                "workspace/document-templates/compact/dsw-science-europe-1.30.1/"
                "artifact.txt"
            ),
        )
        == "compact v1.30.1\n"
    )
    assert (
        _git_show(
            translation_repo,
            (
                "translation/v1.30.1:"
                "workspace/document-templates/translation/dsw-science-europe-1.30.1/"
                "translator.txt"
            ),
        )
        == "manual translation\n"
    )


def _load_sync_module(repo_root: Path) -> ModuleType:
    module_path = repo_root / "scripts" / "ci" / "sync_translation_version_branches.py"
    spec = importlib.util.spec_from_file_location("sync_translation_version_branches", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_translation_config(path: Path) -> None:
    path.write_text(
        """
schema_version: 1

template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: https://github.com/ds-wizard/science-europe-template.git
  supported_ref_spec: v1.21.0+
  supported_versions:
    - v1.30.1

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
  auto_merge_when_clean: false
""".lstrip(),
        encoding="utf-8",
    )


def _write_clean_artifact(artifact_root: Path, *, version: str) -> None:
    workspace_root = artifact_root / "upstream-workspaces" / "dsw-science-europe" / version
    template_name = f"dsw-science-europe-{version.removeprefix('v')}"
    for kind in ("compact", "expanded", "translation"):
        directory = workspace_root / kind / template_name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "artifact.txt").write_text(f"{kind} {version}\n", encoding="utf-8")


def _run_git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _git_show(repo: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "show", revision],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout
