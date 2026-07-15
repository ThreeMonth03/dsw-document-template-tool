"""Tests for the checked-in GitHub Actions workflow."""

from __future__ import annotations

import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

from dsw_document_template_tool.translation_repository import preview_runtime_matrix


def load_workflow_yaml(path: Path) -> dict[str, object]:
    """Load one workflow YAML file while preserving the `on` key."""

    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_docs_site_uses_furo_theme(repo_root: Path) -> None:
    """The public docs should use the same Sphinx theme family as the KM tool."""

    conf_text = (repo_root / "docs" / "conf.py").read_text(encoding="utf-8")
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]

    assert 'html_theme = "furo"' in conf_text
    assert "furo>=2024,<2027" in dev_dependencies
    assert "sphinx-rtd-theme" not in dev_dependencies


def test_headless_render_regression_workflow(repo_root: Path) -> None:
    """The checked-in workflow should keep pointing at the supported CI path."""

    workflow_path = repo_root / ".github" / "workflows" / "headless_render_regression.yml"
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["push"]["branches"] == ["**"]
    assert workflow["on"]["pull_request"]["branches"] == ["**"]
    assert workflow["on"]["schedule"][0]["cron"] == "30 18 * * *"
    assert workflow["permissions"]["contents"] == "write"
    assert workflow["permissions"]["pull-requests"] == "write"
    assert list(workflow["env"]) == sorted(workflow["env"])
    assert workflow["env"]["UPSTREAM_TEMPLATE_TEST_METAMODEL_VERSION"] == "18.0"
    assert "make install-dev" in workflow_text
    assert "v1.29.1+" in workflow_text
    assert "v1.30.0+" in workflow_text
    assert "v1.21.0+" not in workflow_text
    assert (
        workflow["on"]["workflow_dispatch"]["inputs"]["upstream_template_artifact_refs"]["default"]
        == "v1.29.1+"
    )
    assert "make test-upstream-tags" in workflow_text
    assert "UPSTREAM_TEMPLATE_TEST_METAMODEL_VERSION" in workflow_text
    assert "make discover-upstream-compat" in workflow_text
    assert "UPSTREAM_TEMPLATE_DISCOVERY_REFS" in workflow_text
    assert "UPSTREAM_TEMPLATE_DISCOVERY_REPORT" in workflow_text
    assert "continue-on-error: true" in workflow_text
    assert "Open DSW compatibility probe PR" in workflow_text
    offline_steps = workflow["jobs"]["offline-checks"]["steps"]
    compat_pr_step = next(
        step for step in offline_steps if step["name"] == "Open DSW compatibility probe PR"
    )
    assert compat_pr_step["if"] == (
        "steps.discover_compat.outcome == 'failure' && "
        "(github.event_name == 'schedule' || github.event_name == 'workflow_dispatch' || "
        "github.ref == 'refs/heads/master')"
    )
    assert "github.event_name == 'schedule'" in workflow_text
    assert "github.event_name == 'workflow_dispatch'" in workflow_text
    assert "github.ref == 'refs/heads/master'" in workflow_text
    assert (
        "steps.discover_compat.outcome == 'failure' && github.event_name != 'pull_request'"
        not in workflow_text
    )
    assert '--base "$DEFAULT_BRANCH"' in workflow_text
    assert "scripts/ci/create_dsw_compat_pr.py" in workflow_text
    assert "Fail pull request on unsupported upstream metamodel" in workflow_text
    assert "make test-upstream-compat-tags" not in workflow_text
    assert "make build-upstream-artifacts" in workflow_text
    assert "make generate-compat-ledger" in workflow_text
    assert "UPSTREAM_TEMPLATE_ARTIFACT_METAMODEL_VERSION" in workflow_text
    assert "make render-upstream-artifact-previews" in workflow_text
    render_job = workflow["jobs"]["render-regression"]
    matrix_include = render_job["strategy"]["matrix"]["include"]
    assert matrix_include == preview_runtime_matrix(repo_root / "config" / "dsw-compat.yml")
    assert "# BEGIN GENERATED DSW RUNTIME MATRIX" in workflow_text
    assert "# END GENERATED DSW RUNTIME MATRIX" in workflow_text
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
    assert "run: make render-regression-ci-plan" in workflow_text
    render_steps = render_job["steps"]
    summary_step = next(
        step for step in render_steps if step["name"] == "Summarize preview regression coverage"
    )
    assert summary_step["if"] == "always() && matrix.run_preview_regression == 'true'"
    assert "make summarize-regression-coverage" in summary_step["run"]
    assert "matrix.metamodel_version" in summary_step["run"]
    assert "make render-project" not in workflow_text
    assert "make ci-dsw-logs" in workflow_text
    assert "make stop-ci-dsw" in workflow_text
    assert "secrets.DSW_API_URL" not in workflow_text
    assert "secrets.DSW_API_KEY" not in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert workflow_text.count("include-hidden-files: true") == 2
    assert "Publish clean scaffold release assets" in workflow_text
    publish_step = next(
        step for step in render_steps if step["name"] == "Publish clean scaffold release assets"
    )
    assert publish_step["if"] == (
        "github.event_name == 'schedule' || github.event_name == 'workflow_dispatch' || "
        "github.ref == 'refs/heads/master'"
    )
    assert "scripts/ci/publish_clean_scaffold_releases.py" in workflow_text
    assert "scripts/ci/stage_release_assets.py" not in workflow_text
    assert "for package in" not in workflow_text
    assert "gh release view" not in workflow_text
    assert "gh release upload" not in workflow_text
    assert "python3 -c" not in workflow_text
    assert "active-fallback-document-template" not in workflow_text
    assert "upstream-compat-smoke" not in workflow["jobs"]
    assert "Compatibility refs are advisory" not in workflow_text
    assert "clean-upstream-version-artifacts" in workflow_text
    assert "outputs/compat-ledger/" in workflow_text
    assert "outputs/upstream-workspaces/" in workflow_text
    assert "outputs/document-templates/dsw-science-europe/**/scaffold/" in workflow_text
    assert "outputs/project-render/dsw-science-europe/**/scaffold/" in workflow_text


def test_docs_pages_workflow(repo_root: Path) -> None:
    """The documentation site should deploy through the standard Pages workflow."""

    workflow_path = repo_root / ".github" / "workflows" / "pages.yml"
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["name"] == "Deploy Documentation"
    assert workflow["on"]["push"]["branches"] == ["master"]
    assert "workflow_dispatch" in workflow["on"]
    assert "pull_request" not in workflow["on"]
    assert workflow["permissions"] == {
        "contents": "read",
        "id-token": "write",
        "pages": "write",
    }
    assert workflow["concurrency"]["group"] == "github-pages"

    build_job = workflow["jobs"]["build"]
    assert build_job["runs-on"] == "ubuntu-latest"
    assert "actions/checkout@v5" in workflow_text
    assert 'python-version: "3.13"' in workflow_text
    assert "make install-dev BOOTSTRAP_PYTHON=python" in workflow_text
    assert "make docs" in workflow_text
    assert "actions/configure-pages@v6" in workflow_text
    assert "actions/upload-pages-artifact@v5" in workflow_text
    assert "path: docs/_build/html" in workflow_text

    deploy_job = workflow["jobs"]["deploy"]
    assert deploy_job["needs"] == "build"
    assert "actions/deploy-pages@v5" in workflow_text


def test_dsw_runtime_matrix_sync_helper_detects_and_repairs_drift(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """The workflow runtime matrix should be generated from config."""

    source = repo_root / ".github" / "workflows" / "headless_render_regression.yml"
    workflow_copy = tmp_path / "workflow.yml"
    workflow_copy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "sync_dsw_runtime_matrix.py"),
            "--workflow",
            str(workflow_copy),
            "--check",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    workflow_copy.write_text(
        workflow_copy.read_text(encoding="utf-8").replace(
            'tdk_version: "4.30.2"',
            'tdk_version: "4.30.999"',
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "sync_dsw_runtime_matrix.py"),
            "--workflow",
            str(workflow_copy),
            "--check",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "DSW runtime matrix is out of sync" in result.stderr

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "ci" / "sync_dsw_runtime_matrix.py"),
            "--workflow",
            str(workflow_copy),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert workflow_copy.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


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
    assert services["postgres"]["environment"]["POSTGRES_PASSWORD"].startswith(
        "${DSW_CI_POSTGRES_PASSWORD:"
    )
    assert services["minio"]["environment"]["MINIO_ROOT_PASSWORD"].startswith(
        "${DSW_CI_MINIO_ROOT_PASSWORD:"
    )
    assert "$${MINIO_ROOT_PASSWORD}" in services["minio-init"]["entrypoint"][-1]

    for relative_path in (
        "scripts/ci/dsw_env.sh",
        "scripts/ci/start_dsw.sh",
        "scripts/ci/collect_dsw_logs.sh",
        "scripts/ci/stop_dsw.sh",
    ):
        script_path = repo_root / relative_path
        assert script_path.is_file()
        assert script_path.stat().st_mode & stat.S_IXUSR

    start_script = (repo_root / "scripts" / "ci" / "start_dsw.sh").read_text(
        encoding="utf-8",
    )
    assert 'DSW_CI_API_PORT="${DSW_CI_API_PORT:-3000}"' in start_script
    assert (
        'DSW_API_URL="${DSW_API_URL:-http://localhost:${DSW_CI_API_PORT}/wizard-api}"'
        in start_script
    )
    assert "cat <<'YAML'\ngeneral:" not in start_script
    assert 'source "${DSW_ENV_FILE}"' in start_script
    assert "postgres:postgres" not in start_script
    assert "minioPassword" not in start_script

    env_script = (repo_root / "scripts" / "ci" / "dsw_env.sh").read_text(
        encoding="utf-8",
    )
    assert "openssl rand -hex 16" in env_script
    assert "export DSW_CI_APP_SECRET" in env_script
    assert "postgres:postgres" not in env_script
    assert "minioPassword" not in env_script

    for helper_name in ("collect_dsw_logs.sh", "stop_dsw.sh"):
        helper = (repo_root / "scripts" / "ci" / helper_name).read_text(
            encoding="utf-8",
        )
        assert 'source "${DSW_ENV_FILE}"' in helper


def test_external_translation_sync_example_workflow(repo_root: Path) -> None:
    """The copy-paste external workflow should expose path-based translation/output wiring."""

    workflow_path = (
        repo_root / "examples" / "github-actions" / "document_template_translation_sync.yml"
    )
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")
    migration_script_text = (
        repo_root / "scripts" / "ci" / "create_translation_migration_prs.py"
    ).read_text(encoding="utf-8")

    assert workflow["on"]["pull_request"]["branches"] == ["__VERSION_BRANCH__"]
    assert "workflow_dispatch" in workflow["on"]
    assert "schedule" not in workflow["on"]
    assert "github.event_name == 'schedule'" not in workflow_text
    assert workflow["permissions"]["contents"] == "write"
    assert workflow["permissions"]["statuses"] == "write"
    assert workflow["permissions"]["actions"] == "write"
    assert "releases: write" not in workflow_text
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow_text
    assert "env.REFRESH_TRANSLATION_INPUTS == 'true'" in workflow_text
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert "skip-fork-pr" in workflow["jobs"]
    assert workflow["env"]["TOOLING_REPOSITORY"] == "__TOOLING_REPOSITORY__"
    assert workflow["env"]["TOOLING_REF"] == "__TOOLING_REF__"
    assert workflow["env"]["OPERATIONS_BRANCH"] == "__OPERATIONS_BRANCH__"
    assert workflow["env"]["COMPACT_TEMPLATE_DIR"] == "__COMPACT_TEMPLATE_DIR__"
    assert workflow["env"]["TRANSLATION_TREE_DIR"] == "__TRANSLATION_TREE_DIR__"
    assert workflow["env"]["TRANSLATED_TEMPLATE_DIR"] == "__TRANSLATED_TEMPLATE_DIR__"
    assert workflow["env"]["SOURCE_TEMPLATE_ID"] == "__SOURCE_TEMPLATE_ID__"
    assert (
        workflow["env"]["TRANSLATED_TEMPLATE_ORGANIZATION_ID"]
        == "__TRANSLATED_TEMPLATE_ORGANIZATION_ID__"
    )
    assert workflow["env"]["TRANSLATED_TEMPLATE_ID"] == "__TRANSLATED_TEMPLATE_ID__"
    assert (
        workflow["env"]["TRANSLATED_TEMPLATE_DESCRIPTION"] == "__TRANSLATED_TEMPLATE_DESCRIPTION__"
    )
    assert workflow["env"]["TRANSLATED_TEMPLATE_VERSION"] == "__TRANSLATED_TEMPLATE_VERSION__"
    assert workflow["env"]["TRANSLATION_SOURCE_LANG"] == "__TRANSLATION_SOURCE_LANG__"
    assert workflow["env"]["TRANSLATION_TARGET_LANG"] == "__TRANSLATION_TARGET_LANG__"
    assert workflow["env"]["TRANSLATION_TARGET_LABEL"] == "__TRANSLATION_TARGET_LABEL__"
    assert workflow["env"]["TRANSLATED_TEMPLATE_PACKAGE"] == "__TRANSLATED_TEMPLATE_PACKAGE__"
    assert workflow["env"]["PROJECT_REF"] == (
        "tooling-repo/fixtures/projects/demo/test-project.json"
    )
    assert workflow["env"]["PROJECT_RENDER_OUTPUT"] == "__PROJECT_RENDER_OUTPUT__"
    assert workflow["env"]["DSW_VERSION"] == "__DSW_VERSION__"
    assert workflow["env"]["DSW_TDK_VERSION"] == "__DSW_TDK_VERSION__"
    assert (
        workflow["env"]["UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION"]
        == "__UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION__"
    )
    assert (
        workflow["env"]["UPSTREAM_TEMPLATE_PREVIEW_STRICT"]
        == "__UPSTREAM_TEMPLATE_PREVIEW_STRICT__"
    )
    assert workflow["env"]["PUBLISH_RELEASE_ASSETS"] == "__PUBLISH_RELEASE_ASSETS__"
    assert workflow["env"]["REFRESH_TRANSLATION_INPUTS"] == "__REFRESH_TRANSLATION_INPUTS__"
    assert workflow["env"]["PUBLIC_README_PATH"] == "__PUBLIC_README_PATH__"
    assert "PUBLISH_TARGET_REPOSITORY" not in workflow["env"]
    assert "PUBLISH_TARGET_BRANCH" not in workflow["env"]
    assert "DOCUMENT_TEMPLATE_PUBLISH_TOKEN" not in workflow_text
    assert "Publish translated template source branch" not in workflow_text
    assert "dsw-tdk==$DSW_TDK_VERSION" in workflow_text
    assert "tooling-repo" in workflow_text
    assert "fetch-depth: 0" in workflow_text
    checkout_step = next(
        step
        for step in workflow["jobs"]["translation-sync"]["steps"]
        if step["name"] == "Checkout template repository"
    )
    assert checkout_step["with"]["ref"] == (
        "${{ github.event_name == 'pull_request' && "
        "github.event.pull_request.head.sha || '__VERSION_BRANCH__' }}"
    )
    assert "github.event.pull_request.head.ref" in workflow_text
    assert "github.event.pull_request.head.sha" in workflow_text
    tooling_checkout_step = next(
        step
        for step in workflow["jobs"]["translation-sync"]["steps"]
        if step["name"] == "Checkout DSW document-template tooling"
    )
    assert tooling_checkout_step["id"] == "tooling_checkout"
    for step_name in ("Collect local DSW logs", "Stop local DSW stack"):
        cleanup_step = next(
            step
            for step in workflow["jobs"]["translation-sync"]["steps"]
            if step["name"] == step_name
        )
        assert "steps.tooling_checkout.outcome == 'success'" in cleanup_step["if"]
    assert '.venv/bin/dsw-template-transform" expand' in workflow_text
    assert '.venv/bin/dsw-template-tree" export' in workflow_text
    assert '.venv/bin/dsw-template-tree" import-xliff' not in workflow_text
    assert '.venv/bin/dsw-template-tree" export-xliff' not in workflow_text
    assert '.venv/bin/dsw-template-tree" merge' in workflow_text
    assert "--old-tree" in workflow_text
    assert "--new-tree" in workflow_text
    assert "--source-lang" in workflow_text
    assert "--target-lang" in workflow_text
    assert "FRESH_TRANSLATION_TREE=" in workflow_text
    assert "MERGED_TRANSLATION_TREE=" in workflow_text
    assert '.venv/bin/dsw-template-tree" audit' in workflow_text
    assert "Translation block audit failed" in workflow_text
    assert "Auto-commit repaired translation inputs" in workflow_text
    assert "id: auto_commit" in workflow_text
    assert "chore(sync): refresh document template translations" in workflow_text
    assert 'echo "repaired_sha=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"' in workflow_text
    assert "git add \\" in workflow_text
    assert '"$EXPANDED_TEMPLATE_DIR" \\' in workflow_text
    assert '"$TRANSLATION_TREE_DIR/.translation-tree/manifest.json" \\' in workflow_text
    assert '"$TRANSLATION_TREE_DIR/outline.md" \\' in workflow_text
    assert '"$TRANSLATION_TREE_DIR/tree"' in workflow_text
    assert 'git push origin "HEAD:refs/heads/$TARGET_REF"' in workflow_text
    assert '--target-branch "$GITHUB_REF_NAME"' not in workflow_text
    assert '.venv/bin/dsw-template-tree" sync' in workflow_text
    assert '.venv/bin/dsw-template-tree" audit-output' in workflow_text
    assert "--template-organization-id" in workflow_text
    assert "--template-id" in workflow_text
    assert "--template-name" in workflow_text
    assert "--template-description" in workflow_text
    assert "--template-version" in workflow_text
    assert "--public-readme" in workflow_text
    assert "$HOST_ROOT/$PUBLIC_README_PATH" in workflow_text
    assert "Translation sync failed" in workflow_text
    assert "Translated output structure audit failed" in workflow_text
    assert "GITHUB_STEP_SUMMARY" in workflow_text
    assert "Mark auto-repaired head as validated" in workflow_text
    assert "translation-sync / repaired head" in workflow_text
    assert "statuses/$REPAIRED_SHA" in workflow_text
    assert "Dispatch operations migration" in workflow_text
    assert "github.event_name == 'push' &&" in workflow_text
    dispatch_step = next(
        step
        for step in workflow["jobs"]["translation-sync"]["steps"]
        if step["name"] == "Dispatch operations migration"
    )
    assert dispatch_step["if"] == (
        "github.event_name == 'push' && "
        "!startsWith(github.event.head_commit.message, 'chore: refresh ') && "
        "!startsWith(github.event.head_commit.message, 'chore(sync): carry ') && "
        "!startsWith(github.event.head_commit.message, "
        "'chore(sync): refresh document template translations')"
    )
    assert "!startsWith(github.event.head_commit.message, 'chore: refresh ') &&" in workflow_text
    assert (
        "!startsWith(github.event.head_commit.message, 'chore(sync): carry ') &&"
    ) in workflow_text
    assert 'MIGRATION_COMMIT_PREFIX = "chore(sync): carry "' in migration_script_text
    assert (
        "!startsWith(github.event.head_commit.message, "
        "'chore(sync): refresh document template translations')"
    ) in workflow_text
    assert "gh workflow run document_template_translation_sync.yml" in workflow_text
    assert '--ref "$OPERATIONS_BRANCH"' in workflow_text
    assert "--ref master" not in workflow_text
    assert '-f source_version="v$TRANSLATED_TEMPLATE_VERSION"' in workflow_text
    assert "Operations migration dispatched" in workflow_text
    assert "::error title=Translation sync failed::" in workflow_text
    assert "::error title=Translated output structure audit failed::" in workflow_text
    assert 'dsw-tdk" package' in workflow_text
    assert "make start-ci-dsw" in workflow_text
    assert ".venv/bin/dsw-template-render-project" in workflow_text
    assert "-m dsw_document_template_tool.cli" not in workflow_text
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
    assert "actions/upload-artifact@v7" in workflow_text
    assert "Upload translated template package" in workflow_text
    assert "document-template-package-${{ env.TRANSLATED_TEMPLATE_VERSION }}" in workflow_text
    assert "Upload sample project preview" in workflow_text
    assert "Stage translated template release assets" in workflow_text
    assert "Publish translated template release assets" in workflow_text
    assert "env.PUBLISH_RELEASE_ASSETS == 'true'" in workflow_text
    assert 'release_tag="$TRANSLATED_TEMPLATE_ID-v$TRANSLATED_TEMPLATE_VERSION"' in workflow_text
    assert 'gh release view "$release_tag" --repo "$GITHUB_REPOSITORY"' in workflow_text
    assert 'gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$release_tag"' in workflow_text
    assert "sync_release_tag()" in workflow_text
    assert '"repos/$GITHUB_REPOSITORY/git/refs/tags/$release_tag"' in workflow_text
    assert '-f sha="$release_target"' in workflow_text
    assert '--target "$release_target"' in workflow_text
    assert "-F force=true" in workflow_text
    assert "elif ! create_release; then" in workflow_text
    assert (
        'gh release upload "$release_tag" "$release_dir"/* --repo "$GITHUB_REPOSITORY"'
        in workflow_text
    )
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
