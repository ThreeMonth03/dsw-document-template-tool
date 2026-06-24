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
    control_project = translation_repo / "workspace/projects/test-project.json"
    control_km = translation_repo / "workspace/knowledge-models/root-zh-hant-2.7.0.km"
    control_project.parent.mkdir(parents=True)
    control_km.parent.mkdir(parents=True)
    control_project.write_text("stale downstream project\n", encoding="utf-8")
    control_km.write_text("stale downstream km\n", encoding="utf-8")
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
    assert not _git_path_exists(
        translation_repo,
        "translation/v1.30.2:workspace/projects/test-project.json",
    )
    assert not _git_path_exists(
        translation_repo,
        "translation/v1.30.2:workspace/knowledge-models/root-zh-hant-2.7.0.km",
    )
    workflow_text = _git_show(
        translation_repo,
        "translation/v1.30.2:.github/workflows/document_template_translation_sync.yml",
    )
    assert 'branches: ["translation/v1.30.2"]' in workflow_text
    assert "github.event_name == 'push'" in workflow_text
    assert (
        "COMPACT_TEMPLATE_DIR: workspace/document-templates/compact/dsw-science-europe-1.30.2"
    ) in workflow_text
    assert "TRANSLATED_TEMPLATE_VERSION: 1.30.2" in workflow_text
    assert "document-template-package-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "document-template-preview-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert (
        "PROJECT_RENDER_OUTPUT: outputs/project-render/dsw-science-europe/"
        "v1.30.2/zh-Hant/test-project.pdf"
    ) in workflow_text


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
    stale_project = translation_repo / "workspace/projects/test-project.json"
    stale_km = translation_repo / "workspace/knowledge-models/root-zh-hant-2.7.0.km"
    old_compact.parent.mkdir(parents=True, exist_ok=True)
    old_translation_marker.parent.mkdir(parents=True, exist_ok=True)
    stale_project.parent.mkdir(parents=True, exist_ok=True)
    stale_km.parent.mkdir(parents=True, exist_ok=True)
    old_compact.write_text("old compact\n", encoding="utf-8")
    old_translation_marker.write_text("manual translation\n", encoding="utf-8")
    stale_project.write_text("stale branch-local project\n", encoding="utf-8")
    stale_km.write_text("stale branch-local km\n", encoding="utf-8")
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
    assert not _git_path_exists(
        translation_repo,
        "translation/v1.30.1:workspace/projects/test-project.json",
    )
    assert not _git_path_exists(
        translation_repo,
        "translation/v1.30.1:workspace/knowledge-models/root-zh-hant-2.7.0.km",
    )
    workflow_text = _git_show(
        translation_repo,
        "translation/v1.30.1:.github/workflows/document_template_translation_sync.yml",
    )
    assert 'branches: ["translation/v1.30.1"]' in workflow_text
    assert "github.event_name == 'push'" in workflow_text
    assert "document-template-package-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "document-template-preview-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "Dispatch control-plane migration" in workflow_text
    assert "gh workflow run document_template_translation_sync.yml" in workflow_text
    assert '-f source_version="v$TRANSLATED_TEMPLATE_VERSION"' in workflow_text


def test_version_branch_workflow_uses_version_specific_preview_runtime(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Older metamodel branches should preview with a compatible DSW runtime."""

    sync_module = _load_sync_module(repo_root)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    _write_translation_config(
        checkout / "translation-config.yml",
        supported_versions=("v1.29.1", "v1.30.0"),
    )
    config = sync_module.load_translation_repository_config(checkout / "translation-config.yml")

    sync_module.write_version_branch_workflow(
        checkout=checkout,
        tooling_root=repo_root,
        config=config,
        version="v1.29.1",
        branch="translation/v1.29.1",
    )

    workflow_text = (
        checkout / ".github/workflows/document_template_translation_sync.yml"
    ).read_text(encoding="utf-8")
    assert sync_module.preview_runtime_for_version("v1.29.1").dsw_version == "4.26"
    assert sync_module.preview_runtime_for_version("v1.30.0").dsw_version == "4.30"
    assert 'branches: ["translation/v1.29.1"]' in workflow_text
    assert "PROJECT_REF: tooling-repo/workspace/projects/test-project.json" in workflow_text
    assert 'DSW_VERSION: "4.26"' in workflow_text
    assert 'DSW_TDK_VERSION: "4.26.1"' in workflow_text
    assert 'UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION: "17.1"' in workflow_text
    assert 'UPSTREAM_TEMPLATE_PREVIEW_STRICT: "true"' in workflow_text
    assert (
        "COMPACT_TEMPLATE_DIR: workspace/document-templates/compact/dsw-science-europe-1.29.1"
    ) in workflow_text
    assert "TRANSLATED_TEMPLATE_VERSION: 1.29.1" in workflow_text
    assert "document-template-package-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "document-template-preview-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "Dispatch control-plane migration" in workflow_text
    assert "gh workflow run document_template_translation_sync.yml" in workflow_text


def test_version_branch_workflow_runtime_injection_covers_metamodel_groups(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Generated branch workflows should stay aligned with the tooling runtime matrix."""

    sync_module = _load_sync_module(repo_root)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    _write_translation_config(
        checkout / "translation-config.yml",
        supported_versions=("v1.29.1", "v1.30.0"),
    )
    config = sync_module.load_translation_repository_config(checkout / "translation-config.yml")

    expectations = {
        "v1.29.1": (
            'DSW_VERSION: "4.26"',
            'DSW_TDK_VERSION: "4.26.1"',
            'UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION: "17.1"',
            'UPSTREAM_TEMPLATE_PREVIEW_STRICT: "true"',
        ),
        "v1.30.0": (
            'DSW_VERSION: "4.30"',
            'DSW_TDK_VERSION: "4.30.2"',
            'UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION: "18.0"',
            'UPSTREAM_TEMPLATE_PREVIEW_STRICT: "true"',
        ),
    }
    for version, expected_lines in expectations.items():
        branch = f"translation/{version}"
        sync_module.write_version_branch_workflow(
            checkout=checkout,
            tooling_root=repo_root,
            config=config,
            version=version,
            branch=branch,
        )
        workflow_text = (
            checkout / ".github/workflows/document_template_translation_sync.yml"
        ).read_text(encoding="utf-8")
        assert f'branches: ["{branch}"]' in workflow_text
        for expected_line in expected_lines:
            assert expected_line in workflow_text


def _load_sync_module(repo_root: Path) -> ModuleType:
    module_path = repo_root / "scripts" / "ci" / "sync_translation_version_branches.py"
    spec = importlib.util.spec_from_file_location("sync_translation_version_branches", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_translation_config(
    path: Path,
    *,
    supported_versions: tuple[str, ...] = ("v1.30.1",),
) -> None:
    supported_versions_yaml = "\n".join(f"    - {version}" for version in supported_versions)
    path.write_text(
        f"""
schema_version: 1

template:
  organization_id: dsw
  template_id: science-europe
  upstream_repository: https://github.com/ds-wizard/science-europe-template.git
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


def _git_path_exists(repo: Path, revision: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", revision],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
