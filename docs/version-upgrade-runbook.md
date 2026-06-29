# Version Upgrade Runbook

Use this when upstream `ds-wizard/science-europe-template` publishes a new tag
or changes `metamodelVersion`.

## Current Support Model

- Supported upstream versions start at `v1.29.1`.
- Clean scaffold assets are built from upstream tags.
- Downstream translation repositories consume those scaffolds and own their own
  version branches and publication policy.

`config/dsw-compat.yml` may split that support range across multiple runtime
rows. For example, `v1.29.1` currently uses a DSW 4.26 runtime, while
`v1.30.0+` uses a DSW 4.30 runtime. That is expected: the global support policy
starts at `v1.29.1`, but each metamodel range still needs its own proven DSW and
TDK pairing.

## What Happens Automatically

The tool repo CI:

1. resolves upstream tag ranges such as `v1.29.1+`
2. checks each tag's `template.json`
3. verifies that the tag's `metamodelVersion` is covered by `config/dsw-compat.yml`
4. builds clean compact/expanded/translation scaffolds
5. packages scaffold templates
6. renders preview PDFs when the matching DSW runtime supports the metamodel
7. refreshes clean scaffold GitHub Release assets

Downstream repositories do not become fully version-aware by magic. A clean
scaffold release means this repo can transform and package the upstream tag; it
does not mean any downstream translation branch exists yet.

## Known Metamodel

If CI finds that the new upstream tag uses an already configured metamodel:

1. Confirm the tool repo CI is green.
2. Confirm a clean scaffold release exists:

   ```shell
   gh release view clean-scaffold-dsw-science-europe-vX.Y.Z \
     --repo ThreeMonth03/DSW-document-template-tool
   ```

3. Hand the scaffold to the downstream translation repository using
   [Downstream Integration](downstream-integration.md).

Do not stop after the tool repo release is green. A green clean scaffold means
the upstream template can be transformed and packaged; it does not mean the
translated version exists or has passed translation QA.

## New Metamodel

If CI reports an unsupported metamodel:

1. Read the `discover-upstream-compat` summary.
2. On scheduled runs, manual `workflow_dispatch` runs, or `master` pushes,
   check whether CI opened or updated a DSW compatibility follow-up PR. The PR
   records the discovery report and smoke-test checklist. Feature-branch pushes
   intentionally do not open these automation PRs. The automation branch is
   based on the repository default branch, not the branch that happened to
   trigger the workflow.
3. Check the official DSW document-template metamodel notes linked in the CI
   report.
4. Pick a DSW server image and matching `dsw-tdk` version to smoke-test.
5. Add a runtime row to `config/dsw-compat.yml`.
6. Regenerate the workflow matrix:

   ```shell
   make sync-dsw-runtime-matrix
   ```

7. Run:

   ```shell
   make format-check
   make lint
   make test
   ```

8. Push and confirm tool CI builds clean scaffold release assets for the new tag.

The metamodel notes are advisory. They say when a metamodel became supported,
but they do not prove that upload, preview, package, and PDF render all work for
our exact workflow.

Unsupported metamodels should not break already-supported versions. Matrix jobs
filter artifact builds by their configured metamodel, so existing clean scaffold
release assets can still refresh while the new runtime is being investigated.

## Parser Changes During Upgrade

If the upstream tag forces transform or translation tree changes:

1. Follow [Parser and Translation Tree](parser-and-translation-tree.md).
2. Refresh clean scaffold artifacts.
3. Run exact-only migration into the new branch.
4. Inspect untranslated or changed units.
5. Render the demo PDF.
6. Do not carry fuzzy translations into the new version without review.

## Release Asset Expectations

Tool repo release assets are named like:

```text
clean-scaffold-dsw-science-europe-v1.30.1
```

Assets refresh when CI runs successfully for the relevant upstream tag. The
release Git tag is only a version download bucket; check release notes and
checksums for generated asset provenance.
