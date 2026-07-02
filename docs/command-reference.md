# Command Reference

This page is intentionally command-focused. See the workflow and runbook
documents for context.

Use shell variables for repository locations so commands survive repo moves:

```shell
TOOL_GITHUB_REPO=owner/document-template-tool
TRANSLATION_GITHUB_REPO=owner/document-template-translation
TOOL_REPO_DIR=$PWD
TRANSLATION_REPO_DIR=/path/to/document-template-translation
```

## Setup and Checks

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

## Transform and Translation Tree

```shell
make transform
make compact-template
make export-translation-tree
make export-fresh-translation-tree
make merge-translation-tree
make export-weblate-xliff
make import-weblate-xliff
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
WEBLATE_XLIFF=weblate/dsw-science-europe.zh_Hant.xlf
```

Direct CLI examples:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/transform_template.py" expand --source compact --output expanded
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" export --source expanded --output translation
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" export-xliff --tree translation --output weblate/dsw-science-europe.zh_Hant.xlf
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" import-xliff --tree translation --xliff weblate/dsw-science-europe.zh_Hant.xlf
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" merge --old-tree old --new-tree fresh --output merged
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" sync --tree translation --source expanded --output output \
  --template-organization-id dsw \
  --template-id science-europe-zh-hant \
  --template-name "Science Europe DMP Template (zh-Hant)" \
  --template-version 1.30.1
```

## Upstream Tags and Clean Scaffold Artifacts

```shell
make list-upstream-template-tags
make fetch-upstream-template UPSTREAM_TEMPLATE_REF=v1.30.1
make test-upstream-tags \
  UPSTREAM_TEMPLATE_TEST_REFS="latest main v1.30.0+" \
  UPSTREAM_TEMPLATE_TEST_METAMODEL_VERSION=18.0
make discover-upstream-compat UPSTREAM_TEMPLATE_DISCOVERY_REFS="v1.29.1+"
make build-upstream-artifacts UPSTREAM_TEMPLATE_ARTIFACT_REFS="v1.29.1+"
make generate-compat-ledger
make generate-regression-config
make render-regression-ci
make render-regression-ci-plan
make render-upstream-artifact-previews
```

`UPSTREAM_TEMPLATE_TEST_*` variables are for the current-metamodel smoke test.
`UPSTREAM_TEMPLATE_ARTIFACT_*` variables are for clean scaffold assets across
all configured runtimes.
Run `make build-upstream-artifacts` before any regression config that points at
`outputs/upstream-workspaces/...`; those workspaces are generated outputs, not
checked-in source files.
Run `make generate-compat-ledger` after building upstream artifacts when you
want a fast offline fingerprint of compact, expanded, expanded-regression, and
translation-tree structure across all built versions. The same target also
writes a regression candidate plan for maintainers who want broader coverage
than a single latest-version regression.
`make render-regression-ci` calls `generate-regression-config` automatically and
uses the latest built upstream version for the active metamodel. To inspect an
older built version, set `UPSTREAM_TEMPLATE_REGRESSION_VERSION`, for example:

```shell
make render-regression-ci UPSTREAM_TEMPLATE_REGRESSION_VERSION=v1.30.0
```

`make render-regression-ci-plan` reads
`outputs/compat-ledger/<template-id>/regression-plan.json` and runs the
recommended versions for the active metamodel. It writes versioned preview
outputs such as `outputs/preview/v1.30.1/...` so repeated runs do not overwrite
each other.

The plan runner uses two fixture profiles. `full` keeps the base config fixture
counts. `smoke` keeps all fixed fixtures but caps generated random fixtures to
`REGRESSION_SMOKE_GENERATED_FIXTURE_COUNT` (default: `20`). Boundary versions,
such as the first version for a metamodel runtime, usually use smoke; latest or
structure-changing versions use full.

```shell
make render-regression-ci-plan REGRESSION_SMOKE_GENERATED_FIXTURE_COUNT=40
```

Validate the plan/config wiring without a DSW server:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/run_regression_plan.py" \
  --base-config config/regression.ci.yml \
  --dry-run \
  --generated-config-dir config \
  --metamodel-version 18.0 \
  --plan outputs/compat-ledger/dsw-science-europe/regression-plan.json \
  --smoke-generated-fixture-count 20 \
  --source-template-id dsw-science-europe \
  --workspace-root outputs/upstream-workspaces/dsw-science-europe
```

Write a compatibility discovery report for probe automation:

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
  PROJECT_REF=fixtures/projects/demo/test-project.json \
  PROJECT_RENDER_TEMPLATE_DIR=outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/dsw-science-europe-zh-hant-1.30.1 \
  PROJECT_RENDER_OUTPUT=outputs/project-render/dsw-science-europe/v1.30.1/zh-Hant/test-project.pdf
```

## Release and Publish Helpers

Stage release assets locally:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/stage_release_assets.py" \
  --output-dir outputs/release-assets/demo \
  --notes-title "Demo release" \
  --asset path/to/template.zip=template.zip \
  --optional-asset path/to/test-project.pdf=test-project.pdf
```

Preview clean scaffold release staging without uploading to GitHub:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/publish_clean_scaffold_releases.py" \
  --repository "$TOOL_GITHUB_REPO" \
  --run-id local \
  --commit-sha "$(git rev-parse HEAD)" \
  --dry-run
```

Manually copy reviewed translated source to a target repository branch:

```shell
make publish-translated-template \
  TRANSLATION_REPO="$TRANSLATION_REPO_DIR" \
  PUBLISH_VERSION=v1.30.1
```

This target pushes a reviewable `sync/v*` branch to the configured downstream
repository. It does not update the downstream default branch and does not import
the template into DSW/depositar.

Download clean scaffold artifacts from the latest successful tool CI run:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/download_clean_scaffold_artifacts.py" \
  --repo "$TOOL_GITHUB_REPO" \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds
```

Download clean scaffold artifacts from an exact tool CI run:

```shell
TOOLING_RUN_ID=28346995193
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/download_clean_scaffold_artifacts.py" \
  --repo "$TOOL_GITHUB_REPO" \
  --run-id "$TOOLING_RUN_ID" \
  --output-dir /tmp/clean-scaffolds
```

Dry-run downstream branch refresh:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/sync_translation_version_branches.py" \
  --repo "$TRANSLATION_REPO_DIR" \
  --tooling-root "$TOOL_REPO_DIR" \
  --clean-artifact-root /tmp/clean-scaffolds \
  --dry-run \
  --refresh-existing
```

Scheduled downstream automation should use the default `--policy-mode auto`.
For an operator-triggered maintenance refresh, add `--policy-mode manual` if the
downstream `translation-config.yml` allows it.

Promote a Weblate review-branch XLIFF into a checked-out version branch:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/promote_weblate_xliff.py" \
  --host-root "$TRANSLATION_REPO_DIR" \
  --tooling-root "$TOOL_REPO_DIR" \
  --target-branch translation/v1.30.1 \
  --weblate-branch weblate/v1.30.1 \
  --compact-template-dir workspace/document-templates/compact/dsw-science-europe-1.30.1 \
  --expanded-template-dir workspace/document-templates/expanded/dsw-science-europe-1.30.1 \
  --translation-tree-dir workspace/document-templates/translation/dsw-science-europe-1.30.1 \
  --weblate-xliff weblate/dsw-science-europe.zh_Hant.xlf \
  --translated-template-dir outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/dsw-science-europe-zh-hant-1.30.1 \
  --template-organization-id dsw \
  --template-id science-europe-zh-hant \
  --template-name "Science Europe DMP Template (zh-Hant)" \
  --template-version 1.30.1 \
  --public-readme workspace/document-templates/public-readme/README.md \
  --source-lang en \
  --target-lang zh_Hant
```

Normally the generated `weblate_translation_promote.yml` workflow runs this for
you. Use the command directly only when debugging Weblate review-branch
promotion.

Dry-run an unsupported metamodel probe report:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/create_dsw_compat_pr.py" \
  --report outputs/upstream-compat/discovery.md \
  --repository "$TOOL_GITHUB_REPO" \
  --dry-run
```
