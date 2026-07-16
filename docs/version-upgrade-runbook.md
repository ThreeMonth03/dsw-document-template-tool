# Version Upgrade Runbook

Use this when upstream `ds-wizard/science-europe-template` publishes a new tag
or changes `metamodelVersion`.

## Current Support Model

- Supported upstream versions start at `v1.29.1`.
- Clean scaffold assets are built from upstream tags.
- The public translated-template repository consumes those scaffolds and owns
  its own `sync/v*` branches, release assets, and publication policy.

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

The public repository does not become fully version-aware by magic. A clean
scaffold release means this repo can transform and package the upstream tag; it
does not mean any public `sync/v*` translation branch exists yet.

## Known Metamodel

If CI finds that the new upstream tag uses an already configured metamodel:

1. Confirm the tool repo CI is green.
2. Confirm a clean scaffold release exists. For a manual single-tag check, set:

   ```shell
   TOOL_GITHUB_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
   CHECK_TAG=vX.Y.Z

   gh release view "clean-scaffold-dsw-science-europe-$CHECK_TAG" \
     --repo "$TOOL_GITHUB_REPO"
   ```

3. If you also operate the public translated-template repository, trigger its
   sync workflow using [Public Template Repository Integration](downstream-integration.md).
   Otherwise, hand off the clean scaffold release link and checksum to that
   repository's operator.

Do not stop after the tool repo release is green. A green clean scaffold means
the upstream template can be transformed and packaged; it does not mean the
translated version exists or has passed translation QA.

## New Metamodel

If CI reports an unsupported metamodel:

1. Read the `discover-upstream-compat` summary.
2. On scheduled runs, manual `workflow_dispatch` runs, or `master` pushes,
   check whether CI opened or updated a DSW compatibility probe PR. The PR
   records the discovery report, adds an optimistic `config/dsw-compat.yml`
   runtime row, copies the previous runtime's pinned Knowledge Model assignment
   into `config/regression-evidence.yml`, and asks CI to test the whole
   assumption. Feature-branch pushes intentionally do not open these automation
   PRs. The automation branch is based on the repository default branch, not the
   branch that happened to trigger the workflow.
   Later scheduled runs reopen the existing probe branch and preserve candidate
   DSW/TDK or KM assignment edits already made there; they do not rebuild the
   probe from an older `master` snapshot.
3. Review the generated runtime row and KM assignment. They are probes, not a
   compatibility guarantee. If CI fails, replace the copied DSW/TDK versions,
   select and pin a more appropriate KM fixture, or patch the compatibility
   layer.
4. Check the official DSW document-template metamodel notes linked in the CI
   report. They are hints, not proof.
5. Regenerate the workflow matrix if you changed `config/dsw-compat.yml`:

   ```shell
   make sync-dsw-runtime-matrix
   ```

6. Run:

   ```shell
   make check
   ```

7. Push and confirm tool CI builds clean scaffold release assets for the new tag.
8. Inspect the full regression coverage, runtime evidence, clean scaffold
   artifacts, and preview output before merging the probe PR.

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
3. Run exact-source synchronization into the new branch.
4. Inspect untranslated or changed units.
5. Render the demo PDF.
6. Do not carry fuzzy translations into the new version without review.

## Release Asset Expectations

Tool repo release assets are named like:

```text
clean-scaffold-dsw-science-europe-v1.30.1
```

Assets refresh when CI runs successfully for the relevant upstream tag. The
release Git tag is a stable version label and is not force-moved during asset
refresh. Check release notes and checksums for generated asset provenance.
