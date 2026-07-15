"""Checks for generated template artifacts and checked-in fixture assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from dsw_document_template_tool.config import load_workflow_config


def test_generated_outputs_are_not_checked_in(repo_root: Path) -> None:
    """Generated build/render outputs should stay as CI artifacts, not source files."""

    result = subprocess.run(
        ["git", "ls-files", "outputs"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )

    assert result.stdout == ""


def test_document_template_workspace_is_generated_and_ignored(repo_root: Path) -> None:
    """Template workspaces should be generated from upstream instead of committed here."""

    tracked = subprocess.run(
        ["git", "ls-files", "workspace/document-templates"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    ignored = subprocess.run(
        ["git", "check-ignore", "workspace/document-templates/example"],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )

    assert tracked.stdout == ""
    assert ignored.returncode == 0


def test_fixture_assets_exist(repo_root: Path) -> None:
    """The repository should keep non-template fixtures that are needed for generation."""

    regression_km_path = repo_root / "fixtures" / "knowledge-models" / "root-2.7.0.km"
    demo_km_path = repo_root / "fixtures" / "knowledge-models" / "root-zh-hant-2.7.0.km"
    project_ref_path = repo_root / "fixtures" / "projects" / "demo" / "test-project.json"
    smoke_events_path = (
        repo_root / "fixtures" / "projects" / "regression" / "empty-project.events.json"
    )
    wrapped_smoke_events_path = (
        repo_root / "fixtures" / "projects" / "regression" / "wrapped-empty-project.events.json"
    )
    font_root = repo_root / "src" / "dsw_document_template_tool" / "resources" / "fonts"
    font_path = font_root / "NotoSansTC-Variable.ttf"
    font_license_path = font_root / "OFL.txt"

    assert regression_km_path.is_file()
    assert demo_km_path.is_file()
    assert project_ref_path.is_file()
    assert smoke_events_path.is_file()
    assert wrapped_smoke_events_path.is_file()
    assert font_path.is_file()
    assert font_license_path.is_file()

    regression_bundle = json.loads(regression_km_path.read_text(encoding="utf-8"))
    demo_bundle = json.loads(demo_km_path.read_text(encoding="utf-8"))
    assert regression_bundle["id"] == "dsw:root:2.7.0"
    assert demo_bundle["id"] == "dsw:root-zh-hant:2.7.0"
    assert hashlib.sha256(regression_km_path.read_bytes()).hexdigest() == (
        "aabca6f7de8ad41cf9989afd25d4827f3de134fb8f0d965fcc6c336cfeb3e965"
    )


def test_shipped_preview_config_targets_generated_upstream_workspace(
    repo_root: Path, monkeypatch
) -> None:
    """The preview config should point at generated behavior-regression artifacts."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_API_KEY", "secret-token")

    config = load_workflow_config(repo_root / "config" / "regression.preview.yml")
    expected_root = repo_root / "outputs" / "upstream-workspaces" / "dsw-science-europe"

    assert (
        Path(config.baseline.value)
        == (expected_root / "v1.30.0" / "compact" / "dsw-science-europe-1.30.0").resolve()
    )
    assert (
        Path(config.candidate.value)
        == (
            expected_root / "v1.30.0" / "expanded-regression" / "dsw-science-europe-1.30.0"
        ).resolve()
    )
    assert Path(config.fixtures[0].project.knowledge_model_package_id).is_file()
    assert [fixture.name for fixture in config.fixtures] == [
        "empty-project",
        "wrapped-empty-project",
        "filled-demo-project",
    ]
    assert config.regression.output_dir == (repo_root / "outputs" / "preview").resolve()
    for fixture in config.fixtures:
        assert fixture.events_file is not None
        assert fixture.events_file.is_file()


def test_shipped_ci_config_includes_random_render_fixtures(repo_root: Path, monkeypatch) -> None:
    """The CI render job should exercise more than the empty questionnaire."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_EMAIL", "albert.einstein@example.com")
    monkeypatch.setenv("DSW_PASSWORD", "password")

    config = load_workflow_config(repo_root / "config" / "regression.ci.yml")

    assert [fixture.name for fixture in config.fixtures] == [
        "empty-project",
        "wrapped-empty-project",
        "filled-demo-project",
    ]
    assert all(fixture.events_file and fixture.events_file.is_file() for fixture in config.fixtures)
    assert len(config.generated_fixtures) == 1
    generated = config.generated_fixtures[0]
    assert generated.name_prefix == "random-project"
    assert generated.count == 80
    assert generated.seed == 20260522
    assert generated.max_events >= 300
    assert generated.max_items_per_list == 3
    assert generated.selection_pool_size > generated.count
    assert generated.require_complete_coverage
    assert Path(generated.project.knowledge_model_package_id).is_file()


def test_shipped_ci_config_uses_ephemeral_local_dsw(repo_root: Path, monkeypatch) -> None:
    """The CI regression config should not require GitHub Actions secrets."""

    monkeypatch.setenv("DSW_API_URL", "http://localhost:3000/wizard-api")
    monkeypatch.setenv("DSW_EMAIL", "albert.einstein@example.com")
    monkeypatch.setenv("DSW_PASSWORD", "password")

    config = load_workflow_config(repo_root / "config" / "regression.ci.yml")
    expected_root = repo_root / "outputs" / "upstream-workspaces" / "dsw-science-europe"

    assert config.api.url == "http://localhost:3000/wizard-api"
    assert config.api.token is None
    assert config.api.email == "albert.einstein@example.com"
    assert config.api.password == "password"
    assert (
        Path(config.baseline.value)
        == (expected_root / "v1.30.0" / "compact" / "dsw-science-europe-1.30.0").resolve()
    )
    assert (
        Path(config.candidate.value)
        == (
            expected_root / "v1.30.0" / "expanded-regression" / "dsw-science-europe-1.30.0"
        ).resolve()
    )
    assert Path(config.fixtures[0].project.knowledge_model_package_id).is_file()
    assert config.regression.cleanup_projects is True
    assert config.regression.output_dir == (repo_root / "outputs" / "preview").resolve()
