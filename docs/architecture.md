# Architecture

This document maps the repository to the maintenance problems it solves. Use it
when deciding where a change belongs.

## Top-Level Shape

- [`src/dsw_document_template_tool/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool)
  contains reusable package code.
- [`src/dsw_document_template_tool/cli/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/cli)
  contains the maintained direct CLI entrypoints used by Make targets and
  downstream workflows.
- [`scripts/ci/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/scripts/ci)
  contains command-line helpers for GitHub Actions and cross-repository
  automation.
- [`config/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/config)
  contains regression, compatibility, lint, and dependency configuration.
- [`examples/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples)
  contains copy-pasteable workflow templates and downstream repository
  documentation templates.
  Updating examples does not update existing downstream branches by itself.
- [`fixtures/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/fixtures)
  contains checked-in demo/regression project fixtures and matching Knowledge
  Model bundles.
- `workspace/` is reserved for local or generated document-template workspaces.
  It should not contain checked-in version workspaces on this tool repo's
  default branch.
- `outputs/` and `.cache/` are generated and ignored.

## Template Transform Layer

Primary package path:

```text
src/dsw_document_template_tool/_template_transform/
```

Important modules:

- [`workspace.py`](../src/dsw_document_template_tool/_template_transform/workspace.py):
  reads and writes compact/expanded template workspaces.
- [`scanner.py`](../src/dsw_document_template_tool/_template_transform/scanner.py):
  scans template files for translatable regions.
- [`markers.py`](../src/dsw_document_template_tool/_template_transform/markers.py):
  writes and reads translation marker comments.
- [`rewrite_rules.py`](../src/dsw_document_template_tool/_template_transform/rewrite_rules.py):
  shared rewrite rule primitives.
- [`branch_groups.py`](../src/dsw_document_template_tool/_template_transform/branch_groups.py),
  [`branch_sentences.py`](../src/dsw_document_template_tool/_template_transform/branch_sentences.py),
  [`inline_conditionals.py`](../src/dsw_document_template_tool/_template_transform/inline_conditionals.py),
  and [`append_sentences.py`](../src/dsw_document_template_tool/_template_transform/append_sentences.py):
  logic for preserving complete translatable sentences across Jinja branches and
  inline optional text.
- [`science_europe.py`](../src/dsw_document_template_tool/_template_transform/science_europe.py):
  Science Europe transform entry point.
- [`science_europe_balanced_rules.py`](../src/dsw_document_template_tool/_template_transform/science_europe_balanced_rules.py)
  and
  [`science_europe_unbalanced_rules.py`](../src/dsw_document_template_tool/_template_transform/science_europe_unbalanced_rules.py):
  local Science Europe rewrite rules for known upstream structures.
- [`localization.py`](../src/dsw_document_template_tool/_template_transform/localization.py):
  target-language output adjustments during transform.

Public package entry point:

```text
src/dsw_document_template_tool/template_transform.py
```

CLI entry point:

```text
src/dsw_document_template_tool/cli/transform_template.py
```

## Translation Tree Layer

Primary package path:

```text
src/dsw_document_template_tool/_translation_tree/
```

Important modules:

- [`extraction.py`](../src/dsw_document_template_tool/_translation_tree/extraction.py):
  extracts marked translatable units from expanded templates.
- [`document.py`](../src/dsw_document_template_tool/_translation_tree/document.py):
  reads and writes translator-facing `translation.md` files.
- [`filesystem.py`](../src/dsw_document_template_tool/_translation_tree/filesystem.py),
  [`store.py`](../src/dsw_document_template_tool/_translation_tree/store.py),
  and [`ids.py`](../src/dsw_document_template_tool/_translation_tree/ids.py):
  stable tree paths and IDs.
- [`manifest.py`](../src/dsw_document_template_tool/_translation_tree/manifest.py),
  [`metadata.py`](../src/dsw_document_template_tool/_translation_tree/metadata.py),
  and [`outline.py`](../src/dsw_document_template_tool/_translation_tree/outline.py):
  generated metadata and review views.
- [`merge.py`](../src/dsw_document_template_tool/_translation_tree/merge.py):
  exact-safe translation migration between old and new trees.
- [`apply.py`](../src/dsw_document_template_tool/_translation_tree/apply.py):
  applies translations back into expanded templates.
- [`placeholders.py`](../src/dsw_document_template_tool/_translation_tree/placeholders.py),
  [`syntax.py`](../src/dsw_document_template_tool/_translation_tree/syntax.py),
  [`tree_audit.py`](../src/dsw_document_template_tool/_translation_tree/tree_audit.py),
  [`structure_audit.py`](../src/dsw_document_template_tool/_translation_tree/structure_audit.py),
  and [`html_structure.py`](../src/dsw_document_template_tool/_translation_tree/html_structure.py):
  safety checks for placeholders, Jinja, and output structure.
- [`output_polish.py`](../src/dsw_document_template_tool/_translation_tree/output_polish.py):
  target-language output cleanup after sync. For zh-Hant it currently removes
  unsafe leftover `|dot` punctuation behavior.
- [`output_readme.py`](../src/dsw_document_template_tool/_translation_tree/output_readme.py):
  user-facing README selection for translated outputs. It copies the downstream
  translation repo's curated README when present and falls back to a generated
  README otherwise.

Public package entry point:

```text
src/dsw_document_template_tool/translation_tree.py
```

CLI entry point:

```text
src/dsw_document_template_tool/cli/translation_tree.py
```

## Render and Regression Layer

- [`render_project.py`](../src/dsw_document_template_tool/render_project.py):
  imports Knowledge Model, template, and project fixtures into DSW and renders a
  PDF preview.
- [`fixture_generator.py`](../src/dsw_document_template_tool/fixture_generator.py):
  creates deterministic generated project fixtures from compiled DSW
  questionnaire models.
- [`html_diff.py`](../src/dsw_document_template_tool/html_diff.py): normalizes
  rendered HTML and reports behavior differences.
- [`workflow.py`](../src/dsw_document_template_tool/workflow.py): shared
  workflow orchestration helpers.
- [`tdk.py`](../src/dsw_document_template_tool/tdk.py): small wrapper utilities
  around `dsw-tdk`.

CLI entry points:

```text
src/dsw_document_template_tool/cli/render_project.py
src/dsw_document_template_tool/cli/render_regression.py
```

## Compatibility and Automation Layer

- [`dsw_compat.py`](../src/dsw_document_template_tool/dsw_compat.py): reads
  [`config/dsw-compat.yml`](../config/dsw-compat.yml) and maps template
  metamodels to DSW/TDK runtimes.
- [`translation_migration.py`](../src/dsw_document_template_tool/translation_migration.py):
  reads translation repo config and computes version branch paths and migration
  plans.

CI helpers in `scripts/ci/` handle GitHub-specific tasks:

- [`discover_dsw_compat.py`](../scripts/ci/discover_dsw_compat.py): checks
  upstream template tags against configured DSW runtimes.
- [`sync_dsw_runtime_matrix.py`](../scripts/ci/sync_dsw_runtime_matrix.py):
  regenerates the GitHub Actions matrix from
  [`config/dsw-compat.yml`](../config/dsw-compat.yml).
- [`sync_translation_version_branches.py`](../scripts/ci/sync_translation_version_branches.py):
  refreshes downstream translation branches from clean scaffold artifacts.
- [`create_translation_migration_prs.py`](../scripts/ci/create_translation_migration_prs.py):
  creates cross-version migration PRs.
- [`download_clean_scaffold_artifacts.py`](../scripts/ci/download_clean_scaffold_artifacts.py):
  downloads tool repo clean scaffold artifacts for downstream workflows.
- [`stage_release_assets.py`](../scripts/ci/stage_release_assets.py): stages
  packages, previews, checksums, and release notes before `gh release upload`.
- [`publish_translated_template.py`](../scripts/ci/publish_translated_template.py):
  manually copies reviewed translated source into a target repository branch.

## Ownership Rules

- If a change affects generated sentence boundaries, it belongs in the transform
  or translation tree layer, not in a downstream translation file.
- If a workflow step needs parsing, branching, GitHub API calls, or
  cross-repository behavior, put it in `scripts/ci/` with tests instead of
  embedding it in YAML.
- If a behavior is specific to one upstream template family, isolate it in a
  named template-specific module rather than a generic utility.
