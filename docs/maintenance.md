# Maintenance Guide

This guide is for maintainers changing infrastructure, parser behavior, CI
helpers, or version migration logic.

## Repository Boundaries

This repo owns reusable tooling. It should not accumulate completed translation
work or public template source.

Keep these paths source-controlled:

- `src/`
- `scripts/ci/`
- `config/`
- `examples/`
- `tests/`
- `workspace/knowledge-models/`
- `workspace/projects/`
- `assets/fonts/`

Keep these paths generated:

- `outputs/`
- `.cache/`
- `workspace/document-templates/`
- Python caches and virtualenvs

Run `make clean` when local generated outputs make inspection noisy.

## CLI Layout

The root scripts in `src/*.py` are thin compatibility shims used by the Makefile,
tests, and downstream workflows. Real CLI logic lives in
`src/dsw_document_template_tool/cli/` or package modules.

Keep shims small. Put parsing, migration, rendering, and workflow behavior in
tested package functions or `scripts/ci/` helpers.

## CI Helper Policy

GitHub Actions YAML should describe the workflow, not implement complicated
logic. If a step needs branching, config parsing, GitHub API calls, or
cross-repository behavior, prefer a tested helper under `scripts/ci/`.

Current downstream-control helpers:

- `validate_translation_config.py`
- `download_clean_scaffold_artifacts.py`
- `sync_translation_version_branches.py`
- `resolve_migration_source.py`
- `create_translation_migration_prs.py`
- `publish_translated_template.py`

When adding a helper, add:

- a `--help` smoke test in `tests/infra/test_cli_entrypoints.py`
- focused behavior tests under `tests/infra/`
- workflow usage that passes paths explicitly

## Parser And Translation Tree Changes

Parser changes can affect existing translations. Treat them like migrations:

1. Run `make test`.
2. Build clean upstream artifacts.
3. Export a fresh translation tree.
4. Merge existing translations with exact-only rules.
5. Inspect `outline.md` and migration reports.
6. Render preview PDFs before asking translators to continue.

Translator-facing files should stay readable. Avoid exposing raw Jinja, branch
fragments, or machine identifiers as the primary visual content. Metadata is
useful, but it should not be the first thing translators have to process.

## Compatibility Updates

`config/dsw-compat.yml` is the single source of truth for DSW runtime support.
Do not guess a runtime from version numbers alone.

When upstream adds a tag:

1. Let `discover-upstream-compat` inspect its `template.json`.
2. If the metamodel is already covered, CI should build artifacts automatically.
3. If the metamodel is new, smoke-test an appropriate DSW server and TDK version.
4. Add a new runtime row to `config/dsw-compat.yml`.
5. Re-run CI and confirm artifacts are produced.

## Standard Checks

Before pushing infra changes:

```shell
make format-check
make lint
make test
git diff --check
```

For changes affecting downstream translation control repos, also dry-run the
control-plane sync against downloaded clean scaffold artifacts:

```shell
tmpdir="$(mktemp -d)"
python scripts/ci/download_clean_scaffold_artifacts.py \
  --repo ThreeMonth03/DSW-document-template-tool \
  --workflow headless_render_regression.yml \
  --output-dir "$tmpdir"

python scripts/ci/sync_translation_version_branches.py \
  --repo ../DSW-document-template-translation-master-control \
  --tooling-root "$PWD" \
  --clean-artifact-root "$tmpdir" \
  --dry-run \
  --refresh-existing
```
