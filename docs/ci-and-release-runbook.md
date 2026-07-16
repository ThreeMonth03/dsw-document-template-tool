# CI and Release Runbook

This runbook explains what this repository's GitHub Actions produce and how
clean scaffold release assets refresh.

## Tool Repo CI

Workflow:

- [`.github/workflows/headless_render_regression.yml`](../.github/workflows/headless_render_regression.yml)

Main jobs:

- `offline-checks`: install dependencies, validate upstream transform/package
  behavior, discover DSW compatibility, run format/lint/tests.
- `render-regression`: run the DSW runtime matrix, build clean scaffold
  artifacts, render previews, upload Actions artifacts, and refresh clean
  scaffold release assets.

Compatibility discovery is intentionally non-destructive on scheduled runs,
manual `workflow_dispatch` runs, and `master` pushes. If a new upstream tag uses
an unsupported `metamodelVersion`, the workflow opens or updates a compatibility
probe PR. That PR records the discovery report, copies the closest previous
DSW/TDK runtime into a candidate
[`config/dsw-compat.yml`](../config/dsw-compat.yml) row, and lets CI test the
assumption. Matrix jobs continue refreshing artifacts for already-supported
metamodels. Ordinary feature-branch pushes do not open automation PRs. Pull
requests still fail on unsupported metamodels so maintainers notice the missing
runtime.

The upstream validation and clean scaffold build both filter refs by the
metamodel handled by the current runtime. This prevents a future unsupported tag
from blocking refreshes for already-supported versions.

The fast upstream validation does not start DSW and is not runtime evidence. A
runtime is supported only after the `render-regression` job passes complete
coverage, package preview, and the final evidence gate.

Clean scaffold releases:

```text
clean-scaffold-dsw-science-europe-v1.29.1
clean-scaffold-dsw-science-europe-v1.30.0
clean-scaffold-dsw-science-europe-v1.30.1
```

These releases are not finished translations. They are inputs for public
repository translation maintenance.

## Release Refresh Semantics

Release assets are overwritten with:

```shell
gh release upload "$release_tag" "$release_dir"/* --repo "$GITHUB_REPOSITORY" --clobber
```

This means:

- branch updates refresh same-version assets
- GitHub Release tags are stable version labels and are created only once
- refreshing a release does not force-move its Git tag
- release notes, checksums, and workflow run metadata remain the provenance
  source of truth

If a repository enables immutable releases, `--clobber` will fail. See
[Troubleshooting](troubleshooting.md).

## Public Repository Integration

The public translated-template repository consumes these clean scaffold releases
and publishes its own translated package/PDF releases. Its version workflow
uses the demo PDF for human review and separately imports the actual translated
package ZIP for complete generated-fixture render regression. The translated
release therefore includes the regression report and coverage JSON alongside
the package, PDF, and checksums. That repository should document its branch
layout, translation QA, and manual import policy.

This repo provides the helper contract in
[Public Template Repository Integration](downstream-integration.md).

## Updating Existing Version Branch Workflows

Changing `examples/github-actions/document_template_translation_sync.yml` only
changes the template copied by the public repository. Existing `sync/v*`
branches each carry their own workflow file. Apply important workflow fixes in
the public repository and confirm that its release assets refresh there.
