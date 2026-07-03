# Troubleshooting

Use this when CI, DSW, render previews, release assets, or audits fail.

## DSW Stack Will Not Start

Symptoms:

- `make start-ci-dsw` fails
- Docker reports port conflicts
- DSW API is unavailable at `localhost:3000`

Actions:

```shell
make ci-dsw-logs
make stop-ci-dsw
```

Use alternate ports locally:

```shell
export DSW_CI_API_PORT=3100
export DSW_CI_MINIO_PORT=9100
export DSW_API_URL=http://localhost:3100/wizard-api
make start-ci-dsw
```

## Metamodel Is Unsupported

Symptoms:

- `discover-upstream-compat` fails
- CI says a template `metamodelVersion` is not covered
- scheduled CI opens or updates an `automation/dsw-compat-probe-*` pull request

Actions:

1. Read the CI summary.
2. Open the generated compatibility probe PR if one exists.
3. Confirm the PR copied the intended previous DSW/TDK runtime into
   `config/dsw-compat.yml`.
4. Let CI smoke-test the candidate. If it fails, check the official DSW
   metamodel notes linked in the summary, then update the DSW server image,
   matching TDK version, or compatibility code.
5. Run `make sync-dsw-runtime-matrix` after any manual config edit.

Do not merge a probe only because the version number looks plausible. The probe
is useful because CI tests the assumption.

Existing release assets are not deleted by this failure. The new upstream tag is
blocked until a runtime is proven, while already-supported metamodel ranges can
continue refreshing.

## Translation Audit Fails

Symptoms:

- raw Jinja appears in a `translation.md`
- a translation block is malformed
- a sentence is split by branch logic

Actions:

1. Open the exact file from the audit message.
2. If the Markdown block is broken, regenerate the tree.
3. If the source unit is structurally bad, fix transform/export logic instead
   of hand-editing generated Markdown.
4. Re-run:

   ```shell
   make audit-translation-tree
   ```

## Sync or Output Audit Fails

Symptoms:

- missing placeholder
- new placeholder introduced
- executable Jinja or HTML structure changed
- static asset drift

Actions:

1. Check the failing `translation.md`.
2. Restore required placeholders such as `{name}`.
3. Avoid writing raw Jinja in translations.
4. Run:

   ```shell
   make sync-translation-tree
   make audit-translated-template
   ```

## Render Preview Fails

Symptoms:

- PDF is missing
- `failed.json` appears under `outputs/project-render/...`
- DSW document worker errors

Actions:

1. Inspect `failed.json`.
2. Inspect `outputs/ci-dsw/`.
3. Confirm template `metamodelVersion` matches the DSW runtime.
4. Confirm KM bundle and project fixture are compatible.
5. Re-run with a clean DSW stack.

## Release Upload Fails

Symptoms:

- `Publish ... release assets` step fails
- `gh release view` says not a git repository
- `Release.tag_name already exists`
- `gh release upload --clobber` fails

Actions:

1. Confirm workflow commands pass `--repo "$GITHUB_REPOSITORY"` to `gh release`.
2. Confirm workflow has `permissions: contents: write`.
3. Confirm release assets were staged under `outputs/release-assets/...`.
4. If `Release.tag_name already exists` appears, confirm the workflow template
   contains the create-then-edit fallback. This handles the case where the Git
   tag already exists or GitHub release APIs are briefly inconsistent.
5. If GitHub immutable releases are enabled, `--clobber` cannot overwrite
   assets. Disable immutability for these CI download-bucket releases or switch
   to run-id-specific release tags.

## Scheduled Workflows Do Not Run Where Expected

GitHub scheduled workflows run from the repository default branch. Do not assume
a schedule declared only on a non-default version branch will run there.

Use branch push, `workflow_dispatch`, or a default-branch control workflow when
you need to refresh version branches.

## Release Asset Looks Stale

Remember:

- release assets are refreshed only by successful scheduled runs, manual
  `workflow_dispatch` runs, and `master` pushes
- release Git tags are version buckets and may still point at an older commit
- provenance should be checked in release notes, checksums, and workflow run
  metadata

If the asset is stale:

1. Confirm the branch CI ran after the change.
2. Confirm the `Stage ... release assets` step used the expected output paths.
3. Confirm the `Publish ... release assets` step used `--clobber`.
