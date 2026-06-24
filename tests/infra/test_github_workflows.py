"""Tests for the checked-in GitHub Actions workflow."""

from __future__ import annotations

import stat
from pathlib import Path

import yaml

from dsw_document_template_tool.translation_migration import preview_runtime_matrix


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
    assert workflow["on"]["schedule"][0]["cron"] == "30 18 * * *"
    assert "make install-dev" in workflow_text
    assert "v1.29.1+" in workflow_text
    assert "v1.30.0+" in workflow_text
    assert "v1.21.0+" not in workflow_text
    assert (
        workflow["on"]["workflow_dispatch"]["inputs"]["upstream_template_artifact_refs"]["default"]
        == "v1.29.1+"
    )
    assert "make test-upstream-tags" in workflow_text
    assert "make test-upstream-compat-tags" not in workflow_text
    assert "make build-upstream-artifacts" in workflow_text
    assert "make render-upstream-artifact-previews" in workflow_text
    render_job = workflow["jobs"]["render-regression"]
    matrix_include = render_job["strategy"]["matrix"]["include"]
    assert matrix_include == preview_runtime_matrix()
    assert "UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION" in workflow_text
    assert (
        render_job["env"]["UPSTREAM_TEMPLATE_PREVIEW_STRICT"]
        == "${{ matrix.strict_project_preview }}"
    )
    assert "dsw-tdk==${{ matrix.tdk_version }}" in workflow_text
    assert "regression-artifacts-metamodel-${{ matrix.metamodel_key }}" in workflow_text
    assert "clean-upstream-version-artifacts-metamodel-${{ matrix.metamodel_key }}" in workflow_text
    assert "git diff --exit-code -- workspace/document-templates/expanded" not in workflow_text
    assert "git status --short -- workspace/document-templates/expanded" not in workflow_text
    assert "git diff --exit-code -- workspace/document-templates/translation" not in workflow_text
    assert "git status --short -- workspace/document-templates/translation" not in workflow_text
    assert "make verify-workspace" not in workflow_text
    assert "make start-ci-dsw" in workflow_text
    assert "make render-regression-ci" in workflow_text
    assert "make render-project" not in workflow_text
    assert "make ci-dsw-logs" in workflow_text
    assert "make stop-ci-dsw" in workflow_text
    assert "secrets.DSW_API_URL" not in workflow_text
    assert "secrets.DSW_API_KEY" not in workflow_text
    assert "actions/upload-artifact@v4" in workflow_text
    assert workflow_text.count("include-hidden-files: true") == 2
    assert "active-fallback-document-template" not in workflow_text
    assert "upstream-compat-smoke" not in workflow["jobs"]
    assert "Compatibility refs are advisory" not in workflow_text
    assert "clean-upstream-version-artifacts" in workflow_text
    assert "outputs/upstream-workspaces/" in workflow_text
    assert "outputs/document-templates/dsw-science-europe/**/scaffold/" in workflow_text
    assert "outputs/project-render/dsw-science-europe/**/scaffold/" in workflow_text


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
    assert workflow["permissions"]["statuses"] == "write"
    assert workflow["permissions"]["actions"] == "write"
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow_text
    assert "github.actor != 'github-actions[bot]' &&" not in workflow_text
    assert "if: ${{ github.actor != 'github-actions[bot]' }}" in workflow_text
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
        "outputs/document-templates/dsw-science-europe/v1.30.0/zh-Hant/"
    )
    assert workflow["env"]["TRANSLATED_TEMPLATE_ORGANIZATION_ID"] == "dsw"
    assert workflow["env"]["TRANSLATED_TEMPLATE_ID"] == "science-europe-zh-hant"
    assert workflow["env"]["TRANSLATED_TEMPLATE_VERSION"] == "1.30.0"
    assert workflow["env"]["TRANSLATION_SOURCE_LANG"] == "en"
    assert workflow["env"]["TRANSLATION_TARGET_LANG"] == "zh_Hant"
    assert "science-europe-zh-hant-1.30.0.zip" in workflow["env"]["TRANSLATED_TEMPLATE_PACKAGE"]
    assert workflow["env"]["PROJECT_REF"] == "tooling-repo/workspace/projects/test-project.json"
    assert workflow["env"]["PROJECT_RENDER_OUTPUT"].startswith(
        "outputs/project-render/dsw-science-europe/v1.30.0/zh-Hant/"
    )
    assert workflow["env"]["DSW_VERSION"] == "4.30"
    assert workflow["env"]["DSW_TDK_VERSION"] == "4.30.2"
    assert workflow["env"]["UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION"] == "18.0"
    assert workflow["env"]["UPSTREAM_TEMPLATE_PREVIEW_STRICT"] == "true"
    assert "dsw-tdk==$DSW_TDK_VERSION" in workflow_text
    assert "tooling-repo" in workflow_text
    assert "fetch-depth: 0" in workflow_text
    assert "github.event.pull_request.head.ref" in workflow_text
    assert 'src/transform_template.py" expand' in workflow_text
    assert 'src/translation_tree.py" export' in workflow_text
    assert 'src/translation_tree.py" merge' in workflow_text
    assert "--old-tree" in workflow_text
    assert "--new-tree" in workflow_text
    assert "--source-lang" in workflow_text
    assert "--target-lang" in workflow_text
    assert "FRESH_TRANSLATION_TREE=" in workflow_text
    assert "MERGED_TRANSLATION_TREE=" in workflow_text
    assert 'src/translation_tree.py" audit' in workflow_text
    assert "Translation block audit failed" in workflow_text
    assert "Auto-commit repaired translation inputs" in workflow_text
    assert "id: auto_commit" in workflow_text
    assert "chore(sync): refresh document template translations" in workflow_text
    assert 'echo "repaired_sha=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"' in workflow_text
    assert (
        'git add "$EXPANDED_TEMPLATE_DIR" '
        '"$TRANSLATION_TREE_DIR/.translation-tree/manifest.json" "$TRANSLATION_TREE_DIR/tree"'
        in workflow_text
    )
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
    assert "Mark auto-repaired head as validated" in workflow_text
    assert "translation-sync / repaired head" in workflow_text
    assert "statuses/$REPAIRED_SHA" in workflow_text
    assert "Dispatch control-plane migration" in workflow_text
    assert "github.event_name == 'push' &&" in workflow_text
    assert "gh workflow run document_template_translation_sync.yml" in workflow_text
    assert "--ref master" in workflow_text
    assert '-f source_version="v$TRANSLATED_TEMPLATE_VERSION"' in workflow_text
    assert "Control-plane migration dispatched" in workflow_text
    assert "::error title=Translation sync failed::" in workflow_text
    assert "::error title=Translated output structure audit failed::" in workflow_text
    assert 'dsw-tdk" package' in workflow_text
    assert "make start-ci-dsw" in workflow_text
    assert "src/render_project.py" in workflow_text
    assert 'case "$PROJECT_REF" in' in workflow_text
    assert 'project_ref_path="$GITHUB_WORKSPACE/$PROJECT_REF"' in workflow_text
    assert '--project-ref "$project_ref_path"' in workflow_text
    assert "scripts/ci/write_preview_status.py" in workflow_text
    assert "--reason render_failed" in workflow_text
    assert 'if [ "$UPSTREAM_TEMPLATE_PREVIEW_STRICT" = "true" ]; then' in workflow_text
    assert "make ci-dsw-logs" in workflow_text
    assert "make stop-ci-dsw" in workflow_text
    assert "Auto-commit generated outputs" not in workflow_text
    assert "chore(sync): refresh generated document outputs" not in workflow_text
    assert 'git add "${output_paths[@]}"' not in workflow_text
    assert '"$TRANSLATION_TREE_DIR/.translation-tree/manifest.json"' in workflow_text
    assert '"$TRANSLATION_TREE_DIR/tree"' in workflow_text
    assert "outline.md" in workflow_text
    assert "merge-report.json" in workflow_text
    assert "actions/upload-artifact@v4" in workflow_text
    assert "Upload translated template package" in workflow_text
    assert "document-template-package-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "Upload sample project preview" in workflow_text
    assert "document-template-preview-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "template-repo/outputs/project-render/" in workflow_text
    assert "if-no-files-found: warn" in workflow_text

    project_ref = workflow["env"]["PROJECT_REF"]
    assert project_ref.startswith("tooling-repo/")
    project_ref_path = repo_root / project_ref.removeprefix("tooling-repo/")
    assert project_ref_path.is_file()
    project_ref_payload = yaml.safe_load(project_ref_path.read_text(encoding="utf-8"))
    events_path = project_ref_path.parent / project_ref_payload["events_file"]
    km_path = project_ref_path.parent / project_ref_payload["knowledge_model_package_id"]
    assert events_path.is_file()
    assert km_path.resolve().is_file()
    assert (
        project_ref_payload["source_project"]["organization_url"]
        == "https://data.depositar.io/organization/rdm-basics"
    )
    assert (
        project_ref_payload["source_project"]["local_project_uuid"]
        == "447decc1-558e-430c-a981-65793d96af8f"
    )
    events = yaml.safe_load(events_path.read_text(encoding="utf-8"))
    assert isinstance(events, list)
    assert len(events) == 490
