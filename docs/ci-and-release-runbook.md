# CI And Release Runbook

This runbook explains what GitHub Actions produce, how release assets refresh,
and how reviewed output reaches depositar.

## Tool Repo CI

Workflow:

```text
.github/workflows/headless_render_regression.yml
```

Main jobs:

- `offline-checks`: install dependencies, smoke-test upstream refs, discover DSW
  compatibility, run format/lint/tests.
- `render-regression`: run the DSW runtime matrix, build clean scaffold
  artifacts, render previews, upload Actions artifacts, and refresh clean
  scaffold release assets.

Clean scaffold releases:

```text
clean-scaffold-dsw-science-europe-v1.29.1
clean-scaffold-dsw-science-europe-v1.30.0
clean-scaffold-dsw-science-europe-v1.30.1
```

These releases are not finished translations. They are inputs for downstream
translation maintenance.

## Translation Repo CI

Each `translation/v*` branch contains a version-specific workflow. On branch
push, it:

1. checks out the branch and tool repo
2. refreshes expanded template and translation tree
3. auto-commits generated repairs when needed
4. audits translation input
5. syncs translations into output template
6. audits translated output structure
7. packages the DSW import zip
8. renders the demo project PDF
9. uploads Actions artifacts
10. refreshes version-specific GitHub Release assets

Translation releases:

```text
science-europe-zh-hant-v1.29.1
science-europe-zh-hant-v1.30.0
science-europe-zh-hant-v1.30.1
```

Expected assets:

- `dsw-science-europe-zh-hant-vX.Y.Z.zip`
- `test-project-vX.Y.Z.pdf`
- `test-project-vX.Y.Z.pdf.json`
- `SHA256SUMS`
- `release-notes.md`

## Release Refresh Semantics

Release assets are overwritten with:

```shell
gh release upload "$release_tag" "$release_dir"/* --repo "$GITHUB_REPOSITORY" --clobber
```

This means:

- branch updates refresh same-version assets
- GitHub Release tags act as version download buckets
- the Git tag commit is not the generated asset source of truth
- release notes and checksums should be used for provenance

If a repository enables immutable releases, `--clobber` will fail. See
[Troubleshooting](troubleshooting.md).

## Manual depositar Publishing

depositar remains manual. After QA:

1. Download the versioned zip from the translation repo release.
2. Verify the checksum from `SHA256SUMS`.
3. Import the zip into the target DSW/depositar environment.
4. Render or inspect a representative project in the target environment.
5. If public source must be updated, use the manual source publish helper:

   ```shell
   make publish-translated-template \
     TRANSLATION_REPO=/path/to/DSW-document-template-translation \
     PUBLISH_VERSION=v1.30.1
   ```

Do not add automatic depositar publication without reviewing
[Security And Permissions](security-and-permissions.md).

## Updating Existing Version Branch Workflows

Changing `examples/github-actions/document_template_translation_sync.yml` only
changes the template. Existing branches such as `translation/v1.29.1`,
`translation/v1.30.0`, and `translation/v1.30.1` each carry their own workflow
file. Apply important workflow fixes to every supported branch.

After updating a branch workflow, push the branch and confirm its release asset
refreshes.
