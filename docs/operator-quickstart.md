# Operator Quickstart

Use this page when you are taking over day-to-day operation of the tooling
repository. It is a routing checklist, not a replacement for the detailed
runbooks.

## What This Repository Owns

This repository owns:

- upstream Science Europe template discovery
- parser and translation-tree infrastructure
- metamodel-to-DSW runtime compatibility
- clean scaffold artifacts and preview PDFs
- demo KM/project fixtures used by CI

It does not own completed Traditional Chinese translations or public depositar
publication. Those live in the downstream translation repository.

## Daily Health Check

1. Check the latest tool CI run:

   ```shell
   gh run list \
     --repo ThreeMonth03/DSW-document-template-tool \
     --workflow headless_render_regression.yml \
     --branch master \
     --limit 3
   ```

2. Confirm these jobs are green:

   - `offline-checks`
   - `render-regression (17-1, ...)`
   - `render-regression (18-0, ...)`

3. Confirm clean scaffold releases exist for supported versions:

   ```shell
   gh release view clean-scaffold-dsw-science-europe-v1.29.1 \
     --repo ThreeMonth03/DSW-document-template-tool
   gh release view clean-scaffold-dsw-science-europe-v1.30.0 \
     --repo ThreeMonth03/DSW-document-template-tool
   gh release view clean-scaffold-dsw-science-europe-v1.30.1 \
     --repo ThreeMonth03/DSW-document-template-tool
   ```

If all three checks pass, the tooling side is healthy.

## When Upstream Publishes a New Tag

1. Wait for the scheduled tool CI or trigger it manually.
2. Confirm the new tag is included in a clean scaffold release.
3. Hand the result to the downstream translation repository.

Start with [Version Upgrade Runbook](version-upgrade-runbook.md), then follow
[Downstream Integration](downstream-integration.md).

Important: a green clean scaffold release only means the upstream template can
be transformed, packaged, and previewed. It does not mean a translated branch or
translated release exists downstream.

## When CI Finds an Unsupported Metamodel

1. Read the `discover-upstream-compat` summary in the failing run.
2. Check whether CI opened a compatibility follow-up PR.
3. Smoke-test a DSW server image and matching `dsw-tdk`.
4. Add the runtime to `config/dsw-compat.yml`.
5. Run:

   ```shell
   make sync-dsw-runtime-matrix
   make format-check
   make lint
   make test
   ```

Then push and confirm CI can build the clean scaffold release for the new tag.

## When Parser or Translation-Tree Logic Changes

Before asking translators to continue, prove the generated tree is still safe:

```shell
make format-check
make lint
make test
make discover-upstream-compat
make build-upstream-artifacts
```

Then run a downstream dry-run against the translation repository:

```shell
python scripts/ci/download_clean_scaffold_artifacts.py \
  --repo ThreeMonth03/DSW-document-template-tool \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds

python scripts/ci/sync_translation_version_branches.py \
  --repo ../DSW-document-template-translation \
  --tooling-root "$PWD" \
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
