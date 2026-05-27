"""Tests for the checked-in GitHub Actions workflow."""

from __future__ import annotations

import stat
from pathlib import Path

import yaml


def load_workflow_yaml(path: Path) -> dict[str, object]:
    """Load one workflow YAML file while preserving the `on` key."""

    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_headless_render_regression_workflow(repo_root: Path) -> None:
    """The checked-in workflow should keep pointing at the supported CI path."""

    workflow_path = repo_root / ".github" / "workflows" / "headless_render_regression.yml"
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["push"]["branches"] == ["**"]
    assert workflow["on"]["pull_request"]["branches"] == ["**"]
    assert "make install-dev" in workflow_text
    assert "make transform" in workflow_text
    assert "make export-translation-tree" in workflow_text
    assert "make sync-translation-tree" in workflow_text
    assert "git diff --exit-code -- workspace/document-templates/expanded" in workflow_text
    assert "git status --short -- workspace/document-templates/expanded" in workflow_text
    assert "git diff --exit-code -- workspace/document-templates/translation" in workflow_text
    assert "git status --short -- workspace/document-templates/translation" in workflow_text
    assert "make verify-workspace" in workflow_text
    assert "make start-ci-dsw" in workflow_text
    assert "make render-regression-ci" in workflow_text
    assert "make ci-dsw-logs" in workflow_text
    assert "make stop-ci-dsw" in workflow_text
    assert "secrets.DSW_API_URL" not in workflow_text
    assert "secrets.DSW_API_KEY" not in workflow_text
    assert "actions/upload-artifact@v4" in workflow_text


def test_ephemeral_dsw_compose_stack_is_checked_in(repo_root: Path) -> None:
    """The CI render job should have everything needed to boot local DSW."""

    compose_path = repo_root / ".github" / "dsw" / "docker-compose.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = compose["services"]

    assert set(services) == {"postgres", "minio", "minio-init", "server", "docworker"}
    assert services["server"]["image"].startswith("datastewardshipwizard/wizard-server:")
    assert services["docworker"]["image"].startswith("datastewardshipwizard/document-worker:")
    assert services["server"]["ports"] == ["127.0.0.1:${DSW_CI_API_PORT:-3000}:3000"]
    assert services["minio"]["ports"] == ["${DSW_CI_MINIO_PORT:-9000}:9000"]
    assert "host.docker.internal:host-gateway" in services["server"]["extra_hosts"]
    assert "host.docker.internal:host-gateway" in services["docworker"]["extra_hosts"]

    for relative_path in (
        "scripts/ci/start_dsw.sh",
        "scripts/ci/collect_dsw_logs.sh",
        "scripts/ci/stop_dsw.sh",
    ):
        script_path = repo_root / relative_path
        assert script_path.is_file()
        assert script_path.stat().st_mode & stat.S_IXUSR


def test_external_translation_sync_example_workflow(repo_root: Path) -> None:
    """The copy-paste external workflow should expose path-based translation/output wiring."""

    workflow_path = (
        repo_root / "examples" / "github-actions" / "document_template_translation_sync.yml"
    )
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["pull_request"]["branches"] == ["master"]
    assert workflow["on"]["schedule"][0]["cron"] == "0 20 * * *"
    assert "workflow_dispatch" not in workflow["on"]
    assert workflow["permissions"]["contents"] == "write"
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow_text
    assert "skip-fork-pr" in workflow["jobs"]
    assert workflow["env"]["TOOLING_REPOSITORY"] == "ThreeMonth03/DSW-document-template-tool"
    assert workflow["env"]["TOOLING_REF"] == "master"
    assert workflow["env"]["COMPACT_TEMPLATE_DIR"].startswith(
        "workspace/document-templates/compact/"
    )
    assert workflow["env"]["TRANSLATION_TREE_DIR"].startswith(
        "workspace/document-templates/translation/"
    )
    assert workflow["env"]["TRANSLATED_TEMPLATE_DIR"].startswith(
        "outputs/document-templates/translated-expanded/"
    )
    assert workflow["env"]["TRANSLATED_TEMPLATE_ORGANIZATION_ID"] == "dsw"
    assert workflow["env"]["TRANSLATED_TEMPLATE_ID"] == "science-europe-zh-hant"
    assert workflow["env"]["TRANSLATED_TEMPLATE_VERSION"] == "1.30.0"
    assert "science-europe-zh-hant-1.30.0.zip" in workflow["env"]["TRANSLATED_TEMPLATE_PACKAGE"]
    assert workflow["env"]["PROJECT_REF"] == "workspace/projects/test-project.json"
    assert workflow["env"]["PROJECT_RENDER_OUTPUT"].startswith("outputs/project-render/")
    assert "tooling-repo" in workflow_text
    assert "fetch-depth: 0" in workflow_text
    assert "github.event.pull_request.head.ref" in workflow_text
    assert 'src/transform_template.py" expand' in workflow_text
    assert 'src/translation_tree.py" export' in workflow_text
    assert 'src/translation_tree.py" audit' in workflow_text
    assert "Translation block audit failed" in workflow_text
    assert "Auto-commit repaired translation inputs" in workflow_text
    assert "chore(sync): refresh document template translations" in workflow_text
    assert 'git add "$EXPANDED_TEMPLATE_DIR" "$TRANSLATION_TREE_DIR"' in workflow_text
    assert 'git push origin "HEAD:$TARGET_REF"' in workflow_text
    assert 'src/translation_tree.py" sync' in workflow_text
    assert 'src/translation_tree.py" audit-output' in workflow_text
    assert "--template-organization-id" in workflow_text
    assert "--template-id" in workflow_text
    assert "--template-name" in workflow_text
    assert "--template-version" in workflow_text
    assert "Translation sync failed" in workflow_text
    assert "Translated output structure audit failed" in workflow_text
    assert "GITHUB_STEP_SUMMARY" in workflow_text
    assert "::error title=Translation sync failed::" in workflow_text
    assert "::error title=Translated output structure audit failed::" in workflow_text
    assert 'dsw-tdk" package' in workflow_text
    assert "make start-ci-dsw" in workflow_text
    assert "src/render_project.py" in workflow_text
    assert "make ci-dsw-logs" in workflow_text
    assert "make stop-ci-dsw" in workflow_text
    assert "Auto-commit generated outputs" in workflow_text
    assert "chore(sync): refresh generated document outputs" in workflow_text
    assert "content_paths=" in workflow_text
    assert 'git add "${output_paths[@]}"' in workflow_text
    assert "zip/PDF-only churn" in workflow_text
    assert '"$TRANSLATION_TREE_DIR/.translation-tree"' in workflow_text
    assert '"$TRANSLATION_TREE_DIR/tree"' in workflow_text
    assert "outline.md" in workflow_text
    assert "actions/upload-artifact@v4" in workflow_text
    assert "generated document outputs" in workflow_text

    project_ref_path = repo_root / workflow["env"]["PROJECT_REF"]
    assert project_ref_path.is_file()
    project_ref = yaml.safe_load(project_ref_path.read_text(encoding="utf-8"))
    events_path = project_ref_path.parent / project_ref["events_file"]
    km_path = project_ref_path.parent / project_ref["knowledge_model_package_id"]
    assert events_path.is_file()
    assert km_path.resolve().is_file()
    assert project_ref["source_project"]["project_uuid"] == "ae12e1c3-d7a9-4185-af97-1c310d7e6aad"
