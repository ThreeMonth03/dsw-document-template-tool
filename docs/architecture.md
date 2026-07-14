# Architecture

This project is operated through Make targets and installed CLI commands. Start
from the workflow you need, then follow the links into the implementation only
when you are changing behavior.

## Entry Point Map

| Workflow | Maintainer entry point | Direct CLI or helper | Main code |
| --- | --- | --- | --- |
| Expand an upstream compact template | `make transform` | `dsw-template-transform` | [`template_transform.py`](../src/dsw_document_template_tool/template_transform.py), [`_template_transform/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/_template_transform) |
| Export, audit, merge, and sync translation trees | `make export-translation-tree`, `make audit-translation-tree`, `make merge-translation-tree`, `make sync-translation-tree` | `dsw-template-tree` | [`translation_tree.py`](../src/dsw_document_template_tool/translation_tree.py), [`_translation_tree/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/_translation_tree) |
| Render one project preview or release package | `make render-project`, `make render-package` | `dsw-template-render-project` | [`render_project.py`](../src/dsw_document_template_tool/render_project.py) |
| Run render regression | `make render-regression`, `make render-regression-ci-plan` | `dsw-template-render-regression` | [`cli/render_regression.py`](../src/dsw_document_template_tool/cli/render_regression.py), [`workflow.py`](../src/dsw_document_template_tool/workflow.py) |
| Build clean upstream scaffold artifacts | `make discover-upstream-compat`, `make build-upstream-artifacts`, `make render-upstream-artifact-previews` | CI helpers under [`scripts/ci/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/scripts/ci) | [`dsw_compat.py`](../src/dsw_document_template_tool/dsw_compat.py), [`compat_ledger.py`](../src/dsw_document_template_tool/compat_ledger.py) |
| Refresh public repository `sync/v*` branches | `make sync-translation-version-branches`, `make check-translation-migrations` | [`sync_translation_version_branches.py`](../scripts/ci/sync_translation_version_branches.py) | [`translation_migration.py`](../src/dsw_document_template_tool/translation_migration.py) |
| Publish clean scaffold release assets | `make publish-clean-scaffold-releases` | [`publish_clean_scaffold_releases.py`](../scripts/ci/publish_clean_scaffold_releases.py) | [`stage_release_assets.py`](../scripts/ci/stage_release_assets.py) |

For exact command syntax, use [Command Reference](command-reference.md). For
where each operation fits in day-to-day maintenance, use
[Operator Quickstart](operator-quickstart.md).

## Repository Shape

- [`src/dsw_document_template_tool/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool) is the
  Python package. Maintained direct CLIs live under
  [`src/dsw_document_template_tool/cli/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/cli).
- [`scripts/ci/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/scripts/ci) contains GitHub Actions helpers and
  cross-repository automation. These scripts may be run directly for debugging,
  but Make targets are the supported operator interface.
- [`config/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/config) contains regression, compatibility, lint, and
  dependency configuration.
- [`fixtures/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/fixtures) contains checked-in demo and regression project
  fixtures plus matching Knowledge Model bundles.
- [`examples/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples) contains public repository workflow and documentation
  templates. Updating an example does not update existing public repository
  branches by itself.
- `workspace/`, `outputs/`, and `.cache/` are generated operator workspaces,
  build outputs, and caches. They should stay out of `master` unless a file is a
  reusable fixture under [`fixtures/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/fixtures).

## Code Layers

### Template Transform

The transform layer expands an upstream compact template into a translation-safe
workspace. It preserves complete translatable sentences around Jinja branches
and records enough metadata for later audits.

Key files:

- [`_template_transform/workspace.py`](../src/dsw_document_template_tool/_template_transform/workspace.py)
  reads and writes compact and expanded template workspaces.
- [`_template_transform/scanner.py`](../src/dsw_document_template_tool/_template_transform/scanner.py)
  scans template files for translatable regions.
- [`_template_transform/markers.py`](../src/dsw_document_template_tool/_template_transform/markers.py)
  writes and reads translation marker comments.
- [`_template_transform/rewrite_rules.py`](../src/dsw_document_template_tool/_template_transform/rewrite_rules.py)
  provides shared rewrite rule primitives.
- [`_template_transform/branch_groups.py`](../src/dsw_document_template_tool/_template_transform/branch_groups.py),
  [`branch_sentences.py`](../src/dsw_document_template_tool/_template_transform/branch_sentences.py),
  [`inline_conditionals.py`](../src/dsw_document_template_tool/_template_transform/inline_conditionals.py),
  and [`append_sentences.py`](../src/dsw_document_template_tool/_template_transform/append_sentences.py)
  keep optional and branched text translatable as whole sentences.
- [`_template_transform/science_europe.py`](../src/dsw_document_template_tool/_template_transform/science_europe.py),
  [`science_europe_balanced_rules.py`](../src/dsw_document_template_tool/_template_transform/science_europe_balanced_rules.py),
  and [`science_europe_unbalanced_rules.py`](../src/dsw_document_template_tool/_template_transform/science_europe_unbalanced_rules.py)
  isolate Science Europe-specific rewrite behavior.
- [`_template_transform/localization.py`](../src/dsw_document_template_tool/_template_transform/localization.py)
  applies target-language output adjustments during transform.

Change this layer when upstream Jinja or HTML structure needs to be split,
joined, or marked differently before translators see it.

### Translation Tree

The translation tree layer owns translator-facing `translation.md` files,
metadata, migration, audits, and final sync back into a translated expanded
template.

Key files:

- [`_translation_tree/extraction.py`](../src/dsw_document_template_tool/_translation_tree/extraction.py)
  extracts marked translatable units from expanded templates.
- [`_translation_tree/document.py`](../src/dsw_document_template_tool/_translation_tree/document.py)
  reads and writes human-facing `translation.md` files.
- [`_translation_tree/filesystem.py`](../src/dsw_document_template_tool/_translation_tree/filesystem.py),
  [`store.py`](../src/dsw_document_template_tool/_translation_tree/store.py), and
  [`ids.py`](../src/dsw_document_template_tool/_translation_tree/ids.py) define
  stable tree paths and IDs.
- [`_translation_tree/manifest.py`](../src/dsw_document_template_tool/_translation_tree/manifest.py),
  [`metadata.py`](../src/dsw_document_template_tool/_translation_tree/metadata.py), and
  [`outline.py`](../src/dsw_document_template_tool/_translation_tree/outline.py)
  generate review metadata and progress views.
- [`_translation_tree/merge.py`](../src/dsw_document_template_tool/_translation_tree/merge.py)
  preserves translations during refresh and performs explicit exact-source
  replacement during cross-version synchronization.
- [`_translation_tree/apply.py`](../src/dsw_document_template_tool/_translation_tree/apply.py)
  applies translations back into expanded templates.
- [`_translation_tree/placeholders.py`](../src/dsw_document_template_tool/_translation_tree/placeholders.py),
  [`syntax.py`](../src/dsw_document_template_tool/_translation_tree/syntax.py),
  [`tree_audit.py`](../src/dsw_document_template_tool/_translation_tree/tree_audit.py),
  [`structure_audit.py`](../src/dsw_document_template_tool/_translation_tree/structure_audit.py),
  and [`html_structure.py`](../src/dsw_document_template_tool/_translation_tree/html_structure.py)
  check placeholders, Jinja, and translated output structure.
- [`_translation_tree/output_polish.py`](../src/dsw_document_template_tool/_translation_tree/output_polish.py)
  performs target-language cleanup after sync. For zh-Hant it removes unsafe
  leftover `|dot` punctuation behavior after the translation has already chosen
  Chinese punctuation.
- [`_translation_tree/output_readme.py`](../src/dsw_document_template_tool/_translation_tree/output_readme.py)
  selects the user-facing README for translated outputs.

Change this layer when the tree format, migration rules, safety checks, output
polish, or translator-facing files need to change.

### Render, Regression, and Fixtures

Rendering and regression prove that a transformed or translated template still
behaves in DSW.

Key files:

- [`render_project.py`](../src/dsw_document_template_tool/render_project.py)
  imports Knowledge Model, template, and project fixtures into DSW and renders a
  PDF preview.
- [`cli/render_regression.py`](../src/dsw_document_template_tool/cli/render_regression.py)
  runs baseline/candidate render comparisons.
- [`fixture_generator.py`](../src/dsw_document_template_tool/fixture_generator.py)
  creates deterministic generated project fixtures from compiled DSW
  questionnaire models.
- [`html_diff.py`](../src/dsw_document_template_tool/html_diff.py) normalizes
  rendered HTML and reports behavior differences.
- [`workflow.py`](../src/dsw_document_template_tool/workflow.py) contains shared
  workflow orchestration helpers.
- [`tdk.py`](../src/dsw_document_template_tool/tdk.py) wraps `dsw-tdk` calls.

Change this layer when previews, regression coverage, fixture handling, or DSW
interaction behavior needs to change.

### Runtime and CI Helpers

The runtime layer maps upstream template metamodels to DSW and `dsw-tdk`
versions, then feeds that mapping into CI and release automation.

Key files:

- [`dsw_compat.py`](../src/dsw_document_template_tool/dsw_compat.py) reads
  [`config/dsw-compat.yml`](../config/dsw-compat.yml).
- [`compat_ledger.py`](../src/dsw_document_template_tool/compat_ledger.py)
  writes compatibility fingerprints for clean scaffold artifacts.
- [`discover_dsw_compat.py`](../scripts/ci/discover_dsw_compat.py) checks
  upstream tags against configured runtimes.
- [`sync_dsw_runtime_matrix.py`](../scripts/ci/sync_dsw_runtime_matrix.py)
  regenerates GitHub Actions matrices from
  [`config/dsw-compat.yml`](../config/dsw-compat.yml).
- [`create_dsw_compat_pr.py`](../scripts/ci/create_dsw_compat_pr.py) opens or
  updates follow-up PRs when new upstream metamodels need runtime confirmation.

Change this layer when upstream versions, DSW runtime support, GitHub Actions
matrices, or release asset staging behavior changes.

## Ownership Rules

- If a change affects sentence boundaries, Jinja branch grouping, or what a
  translator sees, update the transform or translation tree layer and run the
  parser checklist in [Parser and Translation Tree](parser-and-translation-tree.md).
- If a workflow step needs parsing, branching, GitHub API calls, or
  cross-repository behavior, put it in
  [`scripts/ci/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/scripts/ci)
  with tests instead of embedding it only in YAML.
- If a behavior is specific to one upstream template family, isolate it in a
  named template-specific module rather than a generic utility.
- If a command is meant for maintainers, expose it through [`Makefile`](../Makefile)
  and document it in [Command Reference](command-reference.md).
