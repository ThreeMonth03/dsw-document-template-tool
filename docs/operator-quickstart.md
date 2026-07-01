# Operator Quickstart

Use this page when you are taking over day-to-day operation of the tooling
repository. It is the short operational path; detailed context lives in the
linked runbooks.

## Tooling Outputs

This repository produces:

- upstream Science Europe template discovery
- parser and translation-tree infrastructure
- metamodel-to-DSW runtime compatibility
- clean scaffold release assets and preview PDFs
- demo KM/project fixtures used by CI
- helper scripts and workflow templates consumed by translation repositories

Clean scaffold assets are inputs for translation repositories. They are not
finished translated templates.

## Daily Health Check

Set repository names once before copying GitHub commands:

```shell
TOOL_GITHUB_REPO=owner/document-template-tool
TRANSLATION_GITHUB_REPO=owner/document-template-translation
```

1. Check the latest tool CI run:

   ```shell
   gh run list \
     --repo "$TOOL_GITHUB_REPO" \
     --workflow headless_render_regression.yml \
     --branch master \
     --limit 3
   ```

2. Confirm these jobs are green:

   - `offline-checks`
   - one `render-regression (...)` job for each runtime row in
     `config/dsw-compat.yml`

3. Confirm clean scaffold releases exist for the currently supported tags:

   ```shell
   gh release list \
     --repo "$TOOL_GITHUB_REPO" \
     --limit 30 \
     | grep '^clean-scaffold-dsw-science-europe-'
   ```

   The release name pattern is:

   ```text
   clean-scaffold-dsw-science-europe-vX.Y.Z
   ```

If these checks pass, the tool repo has a healthy baseline for versions already
covered by `config/dsw-compat.yml`. New upstream tags and downstream translation
sync still need the upgrade and handoff flow below.

## When Upstream Publishes a New Tag

Set the tag once:

```shell
NEW_TAG=vX.Y.Z
```

### Tooling side

1. Wait for the scheduled tool CI, or trigger it manually:

   ```shell
   gh workflow run headless_render_regression.yml \
     --repo "$TOOL_GITHUB_REPO" \
     --ref master
   ```

2. Check the latest tool CI run. For a tag whose `metamodelVersion` is already
   covered by `config/dsw-compat.yml`, the run should publish a clean scaffold
   release:

   ```shell
   gh release view "clean-scaffold-dsw-science-europe-$NEW_TAG" \
     --repo "$TOOL_GITHUB_REPO"
   ```

3. If the release exists, the tool repo part is complete for that tag. The
   release contains the clean upstream scaffold inputs that translation
   repositories can consume.

### Translation handoff

If you also operate the downstream translation repository, trigger its sync
workflow after the clean scaffold release exists:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_GITHUB_REPO" \
  --ref master
```

That downstream workflow is responsible for updating its own
`translation-config.yml`, creating or refreshing `translation/v*` branches, and
opening migration PRs according to the translation repository policy. Review the
translation repository run there; do not treat the clean scaffold release as a
finished translated template.

Important: a green clean scaffold release only means the upstream template can
be transformed, packaged, and previewed. It does not mean a translated branch or
translated release exists downstream.

Use [Version Upgrade Runbook](version-upgrade-runbook.md) for the full upstream
tag flow and [Downstream Integration](downstream-integration.md) for artifact
handoff details.

## When CI Finds an Unsupported Metamodel

1. Read the `discover-upstream-compat` summary in the tool CI run.
2. Check whether CI opened a compatibility probe PR, usually named
   `automation/dsw-compat-probe-*`.
3. Review the probe PR. It copies the closest previous DSW/TDK runtime into a
   new `config/dsw-compat.yml` row and lets CI test the assumption that the API,
   import, package, preview, and PDF paths still behave the same way.
4. If CI passes, inspect the clean scaffold artifacts and preview output before
   merging. If CI fails, update the probe row with a newer DSW server image,
   matching `dsw-tdk`, or code compatibility fix.
5. Before merging the probe PR, make sure it also ran:

   ```shell
   make sync-dsw-runtime-matrix
   make format-check
   make lint
   make test
   ```

Then merge only after human review. A green probe means the tool repo has a
tested runtime candidate; it is not an auto-merge signal. Only after that should
the translation repository create or refresh a matching version branch.

## When Parser or Translation-Tree Logic Changes

Before asking translators to continue, prove the generated tree is still safe:

```shell
make format-check
make lint
make test
make discover-upstream-compat
make build-upstream-artifacts
make generate-compat-ledger
```

Review `outputs/compat-ledger/dsw-science-europe/summary.md` for unexpected
cross-version changes in expanded blocks, translation units, placeholders, or
missing scaffold packages before handing artifacts to the translation repo.
Then review `outputs/compat-ledger/dsw-science-europe/regression-plan.md` to see
which versions deserve full DSW regression if you need deeper compatibility
coverage than the automated plan-recommended matrix run.

Then run a downstream dry-run against the translation repository:

```shell
TOOL_REPO_DIR=/path/to/document-template-tool
TRANSLATION_REPO_DIR=/path/to/document-template-translation

"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/download_clean_scaffold_artifacts.py" \
  --repo "$TOOL_GITHUB_REPO" \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds

"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/sync_translation_version_branches.py" \
  --repo "$TRANSLATION_REPO_DIR" \
  --tooling-root "$TOOL_REPO_DIR" \
  --clean-artifact-root /tmp/clean-scaffolds \
  --dry-run \
  --refresh-existing
```

Use [Parser and Translation Tree](parser-and-translation-tree.md) for the full
parser-change checklist.

## Do Not

- Do not commit generated `outputs/`, `.cache/`, or generated document-template
  workspaces.
- Do not edit generated workflow matrix rows by hand; update
  `config/dsw-compat.yml` and run `make sync-dsw-runtime-matrix`.
- Do not treat clean scaffold releases as translated releases.
- Do not add downstream publication tokens to this repo without updating
  [Security and Permissions](security-and-permissions.md).
