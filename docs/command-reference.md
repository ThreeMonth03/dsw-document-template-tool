# Command Reference

This page is intentionally command-focused. See the workflow and runbook
documents for context.

## Setup And Checks

```shell
make install-dev
make format
make format-check
make lint
make test
make test-infra
make test-unit
git diff --check
```

## DSW Stack

```shell
make start-ci-dsw
make ci-dsw-logs
make stop-ci-dsw
```

If local ports conflict:

```shell
export DSW_CI_API_PORT=3100
export DSW_CI_MINIO_PORT=9100
export DSW_API_URL=http://localhost:3100/wizard-api
```

## Transform And Translation Tree

```shell
make transform
make compact-template
make export-translation-tree
make export-fresh-translation-tree
make merge-translation-tree
make audit-translation-tree
make sync-translation-tree
make audit-translated-template
```

Useful variables:

```shell
SOURCE_TEMPLATE_VERSION=1.30.1
SOURCE_TEMPLATE_VERSION_TAG=v1.30.1
COMPACT_TEMPLATE_DIR=workspace/document-templates/compact/dsw-science-europe-1.30.1
EXPANDED_TEMPLATE_DIR=workspace/document-templates/expanded/dsw-science-europe-1.30.1
TRANSLATION_TREE_DIR=workspace/document-templates/translation/dsw-science-europe-1.30.1
```

Direct CLI examples:

```shell
python src/transform_template.py expand --source compact --output expanded
python src/translation_tree.py export --source expanded --output translation
python src/translation_tree.py merge --old-tree old --new-tree fresh --output merged
python src/translation_tree.py sync --tree translation --source expanded --output output \
  --template-organization-id dsw \
  --template-id science-europe-zh-hant \
  --template-name "Science Europe DMP Template (zh-Hant)" \
  --template-version 1.30.1
```

## Upstream Tags And Clean Scaffold Artifacts

```shell
make list-upstream-template-tags
make fetch-upstream-template UPSTREAM_TEMPLATE_REF=v1.30.1
make test-upstream-tags \
  UPSTREAM_TEMPLATE_TEST_REFS="latest main v1.30.0+" \
  UPSTREAM_TEMPLATE_TEST_METAMODEL_VERSION=18.0
make discover-upstream-compat UPSTREAM_TEMPLATE_DISCOVERY_REFS="v1.29.1+"
make build-upstream-artifacts UPSTREAM_TEMPLATE_ARTIFACT_REFS="v1.29.1+"
make render-upstream-artifact-previews
```

`UPSTREAM_TEMPLATE_TEST_*` variables are for the current-metamodel smoke test.
`UPSTREAM_TEMPLATE_ARTIFACT_*` variables are for clean scaffold assets across
all configured runtimes.

Write a compatibility discovery report for follow-up automation:

```shell
make discover-upstream-compat \
  UPSTREAM_TEMPLATE_DISCOVERY_REFS="v1.29.1+" \
  UPSTREAM_TEMPLATE_DISCOVERY_REPORT=outputs/upstream-compat/discovery.md
```

## DSW Runtime Matrix

```shell
make sync-dsw-runtime-matrix
make check-dsw-runtime-matrix
```

The matrix source is `config/dsw-compat.yml`. Do not hand-edit the generated
matrix block in `.github/workflows/headless_render_regression.yml`.

## Render Preview

```shell
make render-project \
  PROJECT_REF=workspace/projects/test-project.json \
  PROJECT_RENDER_TEMPLATE_DIR=outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/dsw-science-europe-zh-hant-1.30.1 \
  PROJECT_RENDER_OUTPUT=outputs/project-render/dsw-science-europe/v1.30.1/zh-Hant/test-project.pdf
```

## Release And Publish Helpers

Stage release assets locally:

```shell
python scripts/ci/stage_release_assets.py \
  --output-dir outputs/release-assets/demo \
  --notes-title "Demo release" \
  --asset path/to/template.zip=template.zip \
  --optional-asset path/to/test-project.pdf=test-project.pdf
```

Stage clean scaffold release assets without uploading to GitHub:

```shell
python scripts/ci/publish_clean_scaffold_releases.py \
  --repository ThreeMonth03/DSW-document-template-tool \
  --run-id local \
  --commit-sha "$(git rev-parse HEAD)" \
  --dry-run
```

Manually copy reviewed translated source to a target repository branch:

```shell
make publish-translated-template \
  TRANSLATION_REPO=/path/to/DSW-document-template-translation \
  PUBLISH_VERSION=v1.30.1
```

Download clean scaffold artifacts from the latest successful tool CI run:

```shell
python scripts/ci/download_clean_scaffold_artifacts.py \
  --repo ThreeMonth03/DSW-document-template-tool \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds
```

Dry-run downstream branch refresh:

```shell
python scripts/ci/sync_translation_version_branches.py \
  --repo ../DSW-document-template-translation-master-control \
  --tooling-root "$PWD" \
  --clean-artifact-root /tmp/clean-scaffolds \
  --dry-run \
  --refresh-existing
```

Dry-run an unsupported metamodel follow-up report:

```shell
python scripts/ci/create_dsw_compat_pr.py \
  --report outputs/upstream-compat/discovery.md \
  --repository ThreeMonth03/DSW-document-template-tool \
  --dry-run
```
