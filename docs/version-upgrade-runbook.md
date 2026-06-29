# Version Upgrade Runbook

Use this when upstream `ds-wizard/science-europe-template` publishes a new tag
or changes `metamodelVersion`.

## Current Support Model

- Supported upstream versions start at `v1.29.1`.
- Tool repo clean scaffold assets are built from upstream tags.
- Translation repo versions are explicit branches such as `translation/v1.30.1`.
- depositar import is manual after review.

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

The translation repo does not become fully version-aware by magic. A new version
must be added to `translation-config.yml`, must get a `translation/v*` branch,
and must publish its own package/PDF release assets before it is considered
ready for manual depositar import.

## Known Metamodel

If CI finds that the new upstream tag uses an already configured metamodel:

1. Confirm the tool repo CI is green.
2. Confirm a clean scaffold release exists:

   ```shell
   gh release view clean-scaffold-dsw-science-europe-vX.Y.Z \
     --repo ThreeMonth03/DSW-document-template-tool
   ```

3. Update the translation repo control config to include `vX.Y.Z`.
4. Run or let the translation control workflow create or refresh the matching
   `translation/vX.Y.Z` branch.
5. Confirm the branch CI publishes:

   ```shell
   gh release view science-europe-zh-hant-vX.Y.Z \
     --repo ThreeMonth03/DSW-document-template-translation
   ```

6. Review migration results and demo PDF before manual depositar import.

Do not stop after the tool repo release is green. A green clean scaffold means
the upstream template can be transformed and packaged; it does not mean the
translated version exists or has passed translation QA.

## New Metamodel

If CI reports an unsupported metamodel:

1. Read the `discover-upstream-compat` summary.
2. Check the official DSW document-template metamodel notes linked in the CI
   report.
3. Pick a DSW server image and matching `dsw-tdk` version to smoke-test.
4. Add a runtime row to `config/dsw-compat.yml`.
5. Regenerate the workflow matrix:

   ```shell
   make sync-dsw-runtime-matrix
   ```

6. Run:

   ```shell
   make format-check
   make lint
   make test
   ```

7. Push and confirm tool CI builds clean scaffold release assets for the new tag.

The metamodel notes are advisory. They say when a metamodel became supported,
but they do not prove that upload, preview, package, and PDF render all work for
our exact workflow.

## Parser Changes During Upgrade

If the upstream tag forces transform or translation tree changes:

1. Follow [Parser And Translation Tree](parser-and-translation-tree.md).
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

Translation repo release assets are named like:

```text
science-europe-zh-hant-v1.30.1
```

Assets refresh when CI runs successfully for the relevant branch/version. The
release Git tag is only a version download bucket; check release notes and
checksums for generated asset provenance.
