# Architecture

This document maps the repository to the maintenance problems it solves. Use it
when deciding where a change belongs.

## Top-Level Shape

- `src/*.py` contains compatibility shims used by Make targets and downstream
  workflows. Keep these files thin.
- `src/dsw_document_template_tool/` contains reusable package code.
- `scripts/ci/` contains command-line helpers for GitHub Actions and
  cross-repository automation.
- `config/` contains regression, compatibility, lint, and dependency
  configuration.
- `examples/` contains copy-pasteable workflow templates. Updating examples does
  not update existing downstream branches by itself.
- `fixtures/` contains checked-in demo/regression project fixtures and matching
  Knowledge Model bundles.
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

- `workspace.py`: reads and writes compact/expanded template workspaces.
- `scanner.py`: scans template files for translatable regions.
- `markers.py`: writes and reads translation marker comments.
- `rewrite_rules.py`: shared rewrite rule primitives.
- `branch_groups.py`, `branch_sentences.py`, `inline_conditionals.py`,
  `append_sentences.py`: logic for preserving complete translatable sentences
  across Jinja branches and inline optional text.
- `science_europe.py`: Science Europe transform entry point.
- `science_europe_balanced_rules.py` and
  `science_europe_unbalanced_rules.py`: local Science Europe rewrite rules for
  known upstream structures.
- `localization.py`: target-language output adjustments during transform.

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

- `extraction.py`: extracts marked translatable units from expanded templates.
- `document.py`: reads and writes translator-facing `translation.md` files.
- `filesystem.py`, `store.py`, `ids.py`: stable tree paths and IDs.
- `manifest.py`, `metadata.py`, `outline.py`: generated metadata and review
  views.
- `merge.py`: exact-safe translation migration between old and new trees.
- `apply.py`: applies translations back into expanded templates.
- `placeholders.py`, `syntax.py`, `tree_audit.py`, `structure_audit.py`,
  `html_structure.py`: safety checks for placeholders, Jinja, and output
  structure.
- `output_polish.py`: target-language output cleanup after sync. For zh-Hant it
  currently removes unsafe leftover `|dot` punctuation behavior.
- `output_readme.py`: user-facing README selection for translated outputs. It
  copies the downstream translation repo's curated README when present and
  falls back to a generated README otherwise.

Public package entry point:

```text
src/dsw_document_template_tool/translation_tree.py
```

CLI entry point:

```text
src/dsw_document_template_tool/cli/translation_tree.py
```

## Render and Regression Layer

- `render_project.py`: imports Knowledge Model, template, and project fixtures
  into DSW and renders a PDF preview.
- `fixture_generator.py`: creates deterministic generated project fixtures from
  compiled DSW questionnaire models.
- `html_diff.py`: normalizes rendered HTML and reports behavior differences.
- `workflow.py`: shared workflow orchestration helpers.
- `tdk.py`: small wrapper utilities around `dsw-tdk`.

CLI entry points:

```text
src/dsw_document_template_tool/cli/render_regression.py
src/render_project.py
src/render_regression.py
```

## Compatibility and Automation Layer

- `dsw_compat.py`: reads `config/dsw-compat.yml` and maps template metamodels to
  DSW/TDK runtimes.
- `translation_migration.py`: reads translation repo config and computes version
  branch paths and migration plans.

CI helpers in `scripts/ci/` handle GitHub-specific tasks:

- `discover_dsw_compat.py`: checks upstream template tags against configured DSW
  runtimes.
- `sync_dsw_runtime_matrix.py`: regenerates the GitHub Actions matrix from
  `config/dsw-compat.yml`.
- `sync_translation_version_branches.py`: refreshes downstream translation
  branches from clean scaffold artifacts.
- `create_translation_migration_prs.py`: creates cross-version migration PRs.
- `download_clean_scaffold_artifacts.py`: downloads tool repo clean scaffold
  artifacts for downstream workflows.
- `stage_release_assets.py`: stages packages, previews, checksums, and release
  notes before `gh release upload`.
- `publish_translated_template.py`: manually copies reviewed translated source
  into a target repository branch.

## Ownership Rules

- If a change affects generated sentence boundaries, it belongs in the transform
  or translation tree layer, not in a downstream translation file.
- If a workflow step needs parsing, branching, GitHub API calls, or
  cross-repository behavior, put it in `scripts/ci/` with tests instead of
  embedding it in YAML.
- If a behavior is specific to one upstream template family, isolate it in a
  named template-specific module rather than a generic utility.
