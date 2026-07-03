# Command Reference

Use this page when you need a command, not background context. The normal
operator interface is `make`; direct Python entrypoints are for reproducing an
exact workflow step or debugging one tool in isolation.

Repository paths should be variables so commands survive repository transfers:

```shell
TOOL_REPO_DIR=/path/to/document-template-tool
TRANSLATION_REPO_DIR=/path/to/document-template-translation
TOOL_GITHUB_REPO=owner/document-template-tool
```

For workflow context, read the matching runbook first:

| Task | Runbook |
| --- | --- |
| First local setup | [Operator Quickstart](operator-quickstart.md) |
| Upstream tag update | [Version Upgrade Runbook](version-upgrade-runbook.md) |
| CI/release operation | [CI and Release Runbook](ci-and-release-runbook.md) |
| Parser or tree behavior changes | [Parser and Translation Tree](parser-and-translation-tree.md) |
| Translation repo handoff | [Downstream Integration](downstream-integration.md) |

## Local Tooling

| Command | Purpose |
| --- | --- |
| `make install-dev` | Create/update the local virtualenv and install tool dependencies. |
| `make check` | Run format check, lint, infra tests, and unit tests. |
| `make format` | Apply the configured formatter. |
| `make format-check` | Check formatting without changing files. |
| `make lint` | Run static lint checks. |
| `make test` | Run all tests. |
| `make test-infra` | Run CI/workflow/helper-script tests. |
| `make test-unit` | Run package unit tests. |

Build or clean the documentation site:

```shell
make docs
make docs-clean
```

GitHub Pages uses `make docs` through `.github/workflows/pages.yml`.

## DSW Stack

Use the local CI DSW stack only for render and preview work:

```shell
make start-ci-dsw
make ci-dsw-logs
make stop-ci-dsw
```

If ports conflict, set ports before starting the stack:

```shell
export DSW_CI_API_PORT=3100
export DSW_CI_MINIO_PORT=9100
export DSW_API_URL=http://localhost:3100/wizard-api
make start-ci-dsw
```

## Template Workspace

These commands transform upstream Science Europe template source into the
workspace shapes used by translation and regression tooling.

| Command | Purpose |
| --- | --- |
| `make fetch-upstream-template UPSTREAM_TEMPLATE_REF=v1.30.1` | Download one upstream template tag into the workspace. |
| `make verify-template` | Verify the compact template with `dsw-tdk`. |
| `make transform` | Expand compact template source into translation-friendly form. |
| `make verify-workspace` | Verify the transformed workspace. |
| `make compact-template` | Compact expanded source back into uploadable template source. |
| `make package-template` | Package the compact template as a `.zip`. |

The most common version variables are:

```shell
SOURCE_TEMPLATE_VERSION=1.30.1
SOURCE_TEMPLATE_VERSION_TAG=v1.30.1
COMPACT_TEMPLATE_DIR=workspace/document-templates/compact/dsw-science-europe-1.30.1
EXPANDED_TEMPLATE_DIR=workspace/document-templates/expanded/dsw-science-europe-1.30.1
TRANSLATION_TREE_DIR=workspace/document-templates/translation/dsw-science-europe-1.30.1
```

## Translation Tree

Use these targets for local tree maintenance. They preserve source placeholders,
Jinja markers, and branch metadata that normal Markdown editing must not break.

| Command | Purpose |
| --- | --- |
| `make export-translation-tree` | Build an editable translation tree from the expanded template. |
| `make export-fresh-translation-tree` | Build a fresh tree for migration comparison. |
| `make merge-translation-tree` | Carry exact-match translations into a fresh tree. |
| `make audit-translation-tree` | Validate translation-tree structure and placeholders. |
| `make sync-translation-tree` | Render translated template source from `translation.md` files. |
| `make audit-translated-template` | Validate translated output against expanded source structure. |
| `make export-xliff` | Export the tree to an optional XLIFF exchange file. |
| `make import-xliff` | Import edited XLIFF targets back into the tree. |

Version branches treat `translation.md` as canonical. XLIFF is an optional
exchange format, not the default editing workflow.

## Upstream Compatibility

Use these targets to discover upstream tags, build clean scaffold outputs, and
verify DSW runtime compatibility.

| Command | Purpose |
| --- | --- |
| `make list-upstream-template-tags` | List available upstream template tags. |
| `make test-upstream-tags` | Smoke test selected refs for the active metamodel. |
| `make discover-upstream-compat` | Detect upstream refs that need a configured DSW runtime. |
| `make sync-dsw-runtime-matrix` | Regenerate the workflow runtime matrix from config. |
| `make check-dsw-runtime-matrix` | Check that the workflow matrix matches config. |

Typical scheduled-discovery invocation:

```shell
make discover-upstream-compat \
  UPSTREAM_TEMPLATE_DISCOVERY_REFS="v1.29.1+" \
  UPSTREAM_TEMPLATE_DISCOVERY_REPORT=outputs/upstream-compat/discovery.md
```

If discovery finds an unsupported metamodel, the workflow opens a follow-up PR
with a report and smoke-test checklist. It does not auto-merge runtime changes.

## Clean Scaffold Artifacts

Clean scaffold artifacts are generated from upstream tags before any human
translation work. They are the input boundary for downstream translation
repositories.

| Command | Purpose |
| --- | --- |
| `make build-upstream-artifacts` | Build compact, expanded, translation tree, package, and metadata outputs for configured upstream refs. |
| `make render-upstream-artifact-previews` | Render scaffold preview outputs where the configured DSW runtime supports it. |
| `make generate-compat-ledger` | Generate offline structural fingerprints across built versions. |

Example:

```shell
make build-upstream-artifacts UPSTREAM_TEMPLATE_ARTIFACT_REFS="v1.29.1+"
make generate-compat-ledger
make render-upstream-artifact-previews
```

Generated workspaces live under `outputs/`; they are build artifacts, not source
files.

## Regression

Regression compares rendered output between a baseline template and a candidate
template. Build upstream artifacts first when the regression config points at
`outputs/upstream-workspaces/...`.

| Command | Purpose |
| --- | --- |
| `make generate-regression-config` | Generate the active regression config from the newest built compatible version. |
| `make render-regression-ci` | Run the single-version CI regression path. |
| `make render-regression-ci-plan` | Run the compatibility-ledger recommended version plan. |
| `make render-regression` | Run the local configured regression path. |

Run the CI-style path locally:

```shell
make start-ci-dsw
make build-upstream-artifacts UPSTREAM_TEMPLATE_ARTIFACT_REFS="v1.29.1+"
make generate-compat-ledger
make render-regression-ci-plan
make stop-ci-dsw
```

Inspect one specific built version:

```shell
make render-regression-ci UPSTREAM_TEMPLATE_REGRESSION_VERSION=v1.30.1
```

Validate a regression plan without a DSW server:

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

## Render Preview

Render one project with one packaged or unpacked template:

```shell
make render-project \
  PROJECT_REF=fixtures/projects/demo/test-project.json \
  PROJECT_RENDER_TEMPLATE_DIR=outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/dsw-science-europe-zh-hant-1.30.1 \
  PROJECT_RENDER_OUTPUT=outputs/project-render/dsw-science-europe/v1.30.1/zh-Hant/test-project.pdf
```

Preview output should stay under `outputs/project-render/...`.

## Downstream Handoff

These commands help a translation repository consume clean scaffold artifacts.
They do not publish to DSW and do not update public deployment repositories.

Download clean scaffold artifacts from a tool workflow run:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/download_clean_scaffold_artifacts.py" \
  --repo "$TOOL_GITHUB_REPO" \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds
```

Download from an exact run:

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

Check whether exact-only migration would still create branch updates:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/check_translation_migration_status.py" \
  --repo "$TRANSLATION_REPO_DIR" \
  --tooling-root "$TOOL_REPO_DIR" \
  --clean-artifact-root /tmp/clean-scaffolds
```

Add `--fail-on-pending` only when CI should fail on pending migration changes.

Manually copy reviewed translated source to a target branch:

```shell
make publish-translated-template \
  TRANSLATION_REPO="$TRANSLATION_REPO_DIR" \
  PUBLISH_VERSION=v1.30.1
```

The publish target creates or updates a reviewable branch using the configured
downstream `publish.branch_prefix`, currently `sync/v*`.

## Release Helpers

Stage release assets locally:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/stage_release_assets.py" \
  --output-dir outputs/release-assets/demo \
  --notes-title "Demo release" \
  --asset path/to/template.zip=template.zip \
  --optional-asset path/to/test-project.pdf=test-project.pdf
```

Preview clean scaffold release staging without uploading:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/publish_clean_scaffold_releases.py" \
  --repository "$TOOL_GITHUB_REPO" \
  --run-id local \
  --commit-sha "$(git rev-parse HEAD)" \
  --dry-run
```

## Direct CLI Use

Prefer `make` for routine work. Direct Python entrypoints are useful when you
need to reproduce exactly what CI ran, pass uncommon flags, or debug one layer
without the Makefile defaults.

The root scripts under `src/` are compatibility shims. The maintained CLI code
lives in `src/dsw_document_template_tool/cli/`, and the stable package APIs are
listed in the Package Reference section of the Sphinx navigation.

Show help:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/transform_template.py" --help
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" --help
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/render_regression.py" --help
```

Run transform directly:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/transform_template.py" expand \
  --source workspace/document-templates/compact/dsw-science-europe-1.30.1 \
  --output workspace/document-templates/expanded/dsw-science-europe-1.30.1
```

Run translation tree export/sync directly:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" export \
  --source workspace/document-templates/expanded/dsw-science-europe-1.30.1 \
  --output workspace/document-templates/translation/dsw-science-europe-1.30.1

"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/translation_tree.py" sync \
  --tree workspace/document-templates/translation/dsw-science-europe-1.30.1 \
  --source workspace/document-templates/expanded/dsw-science-europe-1.30.1 \
  --output outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/dsw-science-europe-zh-hant-1.30.1 \
  --template-organization-id dsw \
  --template-id science-europe-zh-hant \
  --template-name "Science Europe DMP Template (zh-Hant)" \
  --template-version 1.30.1
```

Run a compatibility PR probe dry-run directly:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/create_dsw_compat_pr.py" \
  --report outputs/upstream-compat/discovery.md \
  --repository "$TOOL_GITHUB_REPO" \
  --dry-run
```

If a direct command becomes common in daily work, wrap it in `make` instead of
copying it into another workflow.
