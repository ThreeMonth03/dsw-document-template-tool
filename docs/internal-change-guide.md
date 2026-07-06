# Internal Change Guide

Use this page when a change goes below the maintainer-facing APIs listed in the
package reference. Internal modules are implementation areas, not stable public
APIs, but each area has a clear owner and test surface.

Start from the behavior you need to change. Read the facade first, then the
support modules and tests named in the same row. Prefer adding or adjusting a
small test before editing support code.

## Change Map

| Behavior | Start With | Internal Area | Tests |
| --- | --- | --- | --- |
| Expand upstream template source into translator-friendly source | [`template_transform.py`][template-transform-py] | [`_template_transform/`][template-transform-dir] | [`tests/unit/test_template_transform.py`][test-template-transform-py], [`tests/unit/test_rewrite_rules.py`][test-rewrite-rules-py] |
| Science Europe sentence rewrite or branch-fragment cleanup | [`_template_transform/science_europe.py`][science-europe-py] | [`science_europe_balanced_rules.py`][science-europe-balanced-py], [`science_europe_unbalanced_rules.py`][science-europe-unbalanced-py], [`rewrite_rules.py`][rewrite-rules-py] | [`tests/unit/test_template_transform.py`][test-template-transform-py], render regression |
| Translation Markdown parse/render format | [`translation_tree.py`][translation-tree-py] | [`_translation_tree/document.py`][tree-document-py], [`_translation_tree/metadata.py`][tree-metadata-py], [`_translation_tree/outline.py`][tree-outline-py] | [`tests/unit/test_translation_tree.py`][test-translation-tree-py], CLI tests under [`tests/infra/`][tests-infra] |
| Translation unit extraction, placeholder handling, or Jinja safety | [`translation_tree.py`][translation-tree-py] | [`extraction.py`][tree-extraction-py], [`placeholders.py`][tree-placeholders-py], [`syntax.py`][tree-syntax-py], [`tree_audit.py`][tree-audit-py] | [`tests/unit/test_translation_tree.py`][test-translation-tree-py], [`tests/unit/test_markers.py`][test-markers-py] |
| Exact-only migration between template versions | [`_translation_tree/merge.py`][tree-merge-py], [`translation_migration.py`][translation-migration-py] | [`scripts/ci/create_translation_migration_prs.py`][migration-prs-py], [`scripts/ci/check_translation_migration_status.py`][migration-status-py] | [`tests/infra/test_translation_migration_prs.py`][test-migration-prs-py], [`tests/infra/test_translation_migration_status.py`][test-migration-status-py] |
| Downstream `translation/v*` branch refresh | [`scripts/ci/sync_translation_version_branches.py`][sync-version-branches-py] | [`examples/github-actions/document_template_translation_sync.yml`][translation-sync-workflow] and version policy config | [`tests/infra/test_translation_version_branch_sync.py`][test-version-branch-sync-py], [`tests/infra/test_github_workflows.py`][test-github-workflows-py] |
| Downstream repository documentation templates | [`examples/translation-repository/`][translation-repo-template-dir] | [`docs/translation-repository-templates.md`][translation-repository-templates-doc] | [`tests/infra/test_documentation_site.py`][test-documentation-site-py] |
| DSW runtime compatibility and unsupported metamodel probes | [`dsw_compat.py`][dsw-compat-py], [`config/dsw-compat.yml`][dsw-compat-yml] | [`scripts/ci/discover_dsw_compat.py`][discover-compat-py], [`scripts/ci/create_dsw_compat_pr.py`][create-compat-pr-py] | [`tests/unit/test_dsw_compat.py`][test-dsw-compat-py], [`tests/infra/test_ci_control_helpers.py`][test-ci-control-py] |
| Clean scaffold artifact generation and release assets | [`scripts/ci/upstream_template_artifacts.py`][upstream-artifacts-py] | [`compat_ledger.py`][compat-ledger-py], [`scripts/ci/publish_clean_scaffold_releases.py`][publish-clean-scaffold-py] | [`tests/unit/test_compat_ledger.py`][test-compat-ledger-py], [`tests/infra/test_stage_release_assets.py`][test-stage-assets-py] |
| Render preview or regression behavior | [`workflow.py`][workflow-py], [`render_project.py`][render-project-py] | [`api.py`][api-py], [`fixture_generator.py`][fixture-generator-py], [`html_diff.py`][html-diff-py] | [`tests/unit/test_workflow.py`][test-workflow-py], [`tests/unit/test_render_project.py`][test-render-project-py], [`tests/unit/test_fixture_generator.py`][test-fixture-generator-py] |
| GitHub Actions template wiring | [`examples/github-actions/`][github-actions-templates] | Installed CLI commands in [`src/dsw_document_template_tool/cli/`][cli-dir] and helper scripts in [`scripts/ci/`][ci-scripts-dir] | [`tests/infra/test_github_workflows.py`][test-github-workflows-py], [`tests/infra/test_cli_entrypoints.py`][test-cli-entrypoints-py] |

## Editing Rules

- Keep user-facing CLI commands declared in [`pyproject.toml`][pyproject] and
  implemented under [`src/dsw_document_template_tool/cli/`][cli-dir].
- Keep GitHub Actions YAML as orchestration. Parsing, branch selection,
  migration policy, release staging, and GitHub API behavior belong in Python.
- Keep generated files under ignored output roots. If a generated file needs to
  be reviewed, turn it into a fixture or release artifact intentionally.
- Update docs and Sphinx API pages in the same commit as behavior changes.
- When parser or translation-tree behavior changes, run unit tests, migration
  dry-run, and at least one preview/regression path before trusting the change.

[api-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/api.py
[ci-scripts-dir]: https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/scripts/ci
[cli-dir]: https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/cli
[compat-ledger-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/compat_ledger.py
[create-compat-pr-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/scripts/ci/create_dsw_compat_pr.py
[discover-compat-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/scripts/ci/discover_dsw_compat.py
[dsw-compat-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/dsw_compat.py
[dsw-compat-yml]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/config/dsw-compat.yml
[fixture-generator-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/fixture_generator.py
[github-actions-templates]: https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples/github-actions
[html-diff-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/html_diff.py
[migration-prs-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/scripts/ci/create_translation_migration_prs.py
[migration-status-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/scripts/ci/check_translation_migration_status.py
[publish-clean-scaffold-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/scripts/ci/publish_clean_scaffold_releases.py
[pyproject]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/pyproject.toml
[render-project-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/render_project.py
[rewrite-rules-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_template_transform/rewrite_rules.py
[science-europe-balanced-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_template_transform/science_europe_balanced_rules.py
[science-europe-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_template_transform/science_europe.py
[science-europe-unbalanced-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_template_transform/science_europe_unbalanced_rules.py
[sync-version-branches-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/scripts/ci/sync_translation_version_branches.py
[template-transform-dir]: https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/_template_transform
[template-transform-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/template_transform.py
[test-ci-control-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_ci_control_helpers.py
[test-cli-entrypoints-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_cli_entrypoints.py
[test-compat-ledger-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_compat_ledger.py
[test-dsw-compat-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_dsw_compat.py
[test-documentation-site-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_documentation_site.py
[test-fixture-generator-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_fixture_generator.py
[test-github-workflows-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_github_workflows.py
[test-markers-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_markers.py
[test-migration-prs-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_translation_migration_prs.py
[test-migration-status-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_translation_migration_status.py
[test-render-project-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_render_project.py
[test-rewrite-rules-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_rewrite_rules.py
[test-stage-assets-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_stage_release_assets.py
[test-template-transform-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_template_transform.py
[test-translation-tree-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_translation_tree.py
[test-version-branch-sync-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/infra/test_translation_version_branch_sync.py
[test-workflow-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/tests/unit/test_workflow.py
[tests-infra]: https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/tests/infra
[translation-migration-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/translation_migration.py
[translation-repo-template-dir]: https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples/translation-repository
[translation-repository-templates-doc]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/docs/translation-repository-templates.md
[translation-sync-workflow]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/examples/github-actions/document_template_translation_sync.yml
[translation-tree-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/translation_tree.py
[tree-audit-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/tree_audit.py
[tree-document-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/document.py
[tree-extraction-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/extraction.py
[tree-merge-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/merge.py
[tree-metadata-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/metadata.py
[tree-outline-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/outline.py
[tree-placeholders-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/placeholders.py
[tree-syntax-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/_translation_tree/syntax.py
[upstream-artifacts-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/scripts/ci/upstream_template_artifacts.py
[workflow-py]: https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/src/dsw_document_template_tool/workflow.py
