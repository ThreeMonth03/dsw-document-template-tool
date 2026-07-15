# Command Reference

Use this page when you need a command, not background context. The normal
operator interface is `make`; direct CLI commands are for reproducing an
exact workflow step or debugging one tool in isolation.

Repository paths should be variables so commands survive repository transfers:

```shell
TOOL_REPO_DIR=/path/to/document-template-tool
PUBLIC_TEMPLATE_REPO_DIR=/path/to/science-europe-template-zh_Hant
TOOL_GITHUB_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
```

For workflow context, read the matching runbook first:

| Task | Runbook |
| --- | --- |
| First local setup | [Operator Quickstart](operator-quickstart.md) |
| Upstream tag update | [Version Upgrade Runbook](version-upgrade-runbook.md) |
| CI/release operation | [CI and Release Runbook](ci-and-release-runbook.md) |
| Config file ownership | [Configuration Reference](configuration-reference.md) |
| Parser or tree behavior changes | [Parser and Translation Tree](parser-and-translation-tree.md) |
| Public repository integration | [Public Template Repository Integration](downstream-integration.md) |

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

GitHub Pages uses `make docs-clean docs` through
[`.github/workflows/pages.yml`](../.github/workflows/pages.yml), then verifies
that `index.html` exists and `README.html` was not generated.

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
| `make explain-transform` | Show the selected template profile and named rewrite groups applied by the latest transform. |
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
| `make create-dsw-compat-pr` | Stage or open the unsupported-metamodel follow-up PR. |

Typical scheduled-discovery invocation:

```shell
make discover-upstream-compat \
  UPSTREAM_TEMPLATE_DISCOVERY_REFS="v1.29.1+" \
  UPSTREAM_TEMPLATE_DISCOVERY_REPORT=outputs/upstream-compat/discovery.md
```

If discovery finds an unsupported metamodel, the workflow opens a follow-up PR
with a report and smoke-test checklist. It does not auto-merge runtime changes.
The report is staged at
[`docs/compatibility/dsw-compatibility-probe.md`](compatibility/dsw-compatibility-probe.md).
Local dry-run:

```shell
make create-dsw-compat-pr \
  COMPAT_PROBE_REPORT=outputs/upstream-compat/discovery.md
```

To push the probe PR branch, set `COMPAT_PROBE_DRY_RUN=false`.

## Clean Scaffold Artifacts

Clean scaffold artifacts are generated from upstream tags before any human
translation work. They are the input boundary for the public
translated-template repository.

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
| `make summarize-regression-coverage` | Summarize existing versioned regression and generated branch-coverage reports. |

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
make render-regression-ci-plan-dry-run
```

Summarize reports already written below `outputs/preview/`:

```shell
make summarize-regression-coverage
```

The command prints Markdown locally. In GitHub Actions it also appends the same
table to `GITHUB_STEP_SUMMARY`.

## Render Preview

Render one project with an expanded source workspace:

```shell
make render-project \
  PROJECT_REF=fixtures/projects/demo/test-project.json \
  PROJECT_RENDER_TEMPLATE_DIR=outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/dsw-science-europe-zh-hant-1.30.1 \
  PROJECT_RENDER_OUTPUT=outputs/project-render/dsw-science-europe/v1.30.1/zh-Hant/test-project.pdf
```

Preview output should stay under `outputs/project-render/...`.

Validate a published release package zip by importing it into local DSW and
rendering the demo project:

```shell
make render-package \
  PROJECT_REF=fixtures/projects/demo/test-project.json \
  PROJECT_RENDER_TEMPLATE_PACKAGE=/tmp/dsw-science-europe-zh-hant-v1.30.1.zip \
  PROJECT_RENDER_OUTPUT=outputs/project-render/dsw-science-europe/v1.30.1/zh-Hant/release-package-test-project.pdf
```

Use `render-project` for source workspaces that `dsw-tdk verify` can read.
Use `render-package` for `.zip` assets downloaded from GitHub Releases.
Do not unzip a release package and pass it as `PROJECT_RENDER_TEMPLATE_DIR`;
DSW package zips store template files inside `template.json`.

## Public Repository Integration

These commands help the public translated-template repository consume clean
scaffold artifacts. They do not publish to DSW.

Download clean scaffold artifacts from a tool workflow run:

```shell
make download-clean-scaffold-artifacts \
  TOOL_GITHUB_REPO="$TOOL_GITHUB_REPO" \
  CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR=/tmp/clean-scaffolds
```

Download from an exact run:

```shell
TOOLING_RUN_ID=28346995193
make download-clean-scaffold-artifacts \
  TOOL_GITHUB_REPO="$TOOL_GITHUB_REPO" \
  CLEAN_SCAFFOLD_ARTIFACT_RUN_ID="$TOOLING_RUN_ID" \
  CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR=/tmp/clean-scaffolds
```

Validate the public repository translation config:

```shell
make validate-translation-config \
  TRANSLATION_REPO="$PUBLIC_TEMPLATE_REPO_DIR"
```

Check that public repository docs still cover the required operations topics:

```shell
make check-translation-repository-docs \
  TRANSLATION_DOCS_REPO="$PUBLIC_TEMPLATE_REPO_DIR"
```

Dry-run public repository branch refresh:

```shell
make sync-translation-version-branches \
  TRANSLATION_REPO="$PUBLIC_TEMPLATE_REPO_DIR" \
  TRANSLATION_CLEAN_ARTIFACT_ROOT=/tmp/clean-scaffolds
```

Check whether exact-source synchronization would still create branch updates:

```shell
make check-translation-migrations \
  TRANSLATION_REPO="$PUBLIC_TEMPLATE_REPO_DIR" \
  TRANSLATION_CLEAN_ARTIFACT_ROOT=/tmp/clean-scaffolds
```

Set `TRANSLATION_MIGRATION_FAIL_ON_PENDING=true` only when CI should fail on
pending cross-version synchronization changes.

## Release Helpers

Stage release assets locally:

```shell
make publish-clean-scaffold-releases
```

The target defaults to `CLEAN_SCAFFOLD_RELEASE_DRY_RUN=true`, so it stages the
release tree without uploading. To publish from a trusted CI/manual context:

```shell
make publish-clean-scaffold-releases \
  TOOL_GITHUB_REPO="$TOOL_GITHUB_REPO" \
  CLEAN_SCAFFOLD_RELEASE_DRY_RUN=false
```

## Direct CLI Use

Prefer `make` for routine work. Direct CLI commands are useful when you
need to reproduce exactly what CI ran, pass uncommon flags, or debug one layer
without the Makefile defaults.

The maintained CLI code lives in
[`src/dsw_document_template_tool/cli/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/cli).
The installed command names are declared in
[`pyproject.toml`](https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/pyproject.toml),
and the stable package APIs are listed in the Package Reference section of the
Sphinx navigation.

Show help:

```shell
"$TOOL_REPO_DIR/.venv/bin/dsw-template-transform" --help
"$TOOL_REPO_DIR/.venv/bin/dsw-template-tree" --help
"$TOOL_REPO_DIR/.venv/bin/dsw-template-render-project" --help
"$TOOL_REPO_DIR/.venv/bin/dsw-template-render-regression" --help
```

Run transform directly:

```shell
"$TOOL_REPO_DIR/.venv/bin/dsw-template-transform" expand \
  --source workspace/document-templates/compact/dsw-science-europe-1.30.1 \
  --output workspace/document-templates/expanded/dsw-science-europe-1.30.1
```

Explain the selected profile and upstream-specific rewrites:

```shell
"$TOOL_REPO_DIR/.venv/bin/dsw-template-transform" explain \
  --source workspace/document-templates/expanded/dsw-science-europe-1.30.1
```

Run translation tree export/sync directly:

```shell
"$TOOL_REPO_DIR/.venv/bin/dsw-template-tree" export \
  --source workspace/document-templates/expanded/dsw-science-europe-1.30.1 \
  --output workspace/document-templates/translation/dsw-science-europe-1.30.1

"$TOOL_REPO_DIR/.venv/bin/dsw-template-tree" sync \
  --tree workspace/document-templates/translation/dsw-science-europe-1.30.1 \
  --source workspace/document-templates/expanded/dsw-science-europe-1.30.1 \
  --output outputs/document-templates/dsw-science-europe/v1.30.1/zh-Hant/dsw-science-europe-zh-hant-1.30.1 \
  --template-organization-id dsw \
  --template-id science-europe-zh-hant \
  --template-name "Science Europe DMP Template (zh-Hant)" \
  --template-description "Science Europe DMP Template 的繁體中文化版本" \
  --template-version 1.30.1
```

If a direct command becomes common in daily work, wrap it in `make` instead of
copying it into another workflow.
