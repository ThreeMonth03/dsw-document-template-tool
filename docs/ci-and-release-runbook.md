# CI And Release Runbook

This runbook explains what this repository's GitHub Actions produce and how
clean scaffold release assets refresh.

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

Compatibility discovery is intentionally non-destructive on scheduled runs,
manual `workflow_dispatch` runs, and `master` pushes. If a new upstream tag uses
an unsupported `metamodelVersion`, the workflow records a report and opens or
updates a follow-up PR, but matrix jobs continue refreshing artifacts for
already-supported metamodels. Ordinary feature-branch pushes do not open
automation PRs. Pull requests still fail on unsupported metamodels so
maintainers notice the missing runtime.

The upstream smoke test and clean scaffold build both filter refs by the
metamodel handled by the current runtime. This prevents a future unsupported tag
from blocking refreshes for already-supported versions.

Clean scaffold releases:

```text
clean-scaffold-dsw-science-europe-v1.29.1
clean-scaffold-dsw-science-europe-v1.30.0
clean-scaffold-dsw-science-europe-v1.30.1
```

These releases are not finished translations. They are inputs for downstream
translation maintenance.

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

## Downstream Handoff

Translation repositories consume these clean scaffold releases and publish their
own translated package/PDF releases. The downstream repository should document
its branch layout, translation QA, and manual import policy.

This repo provides the helper contract in [Downstream Integration](downstream-integration.md).

## Updating Existing Version Branch Workflows

Changing `examples/github-actions/document_template_translation_sync.yml` only
changes the template copied by downstream repositories. Existing downstream
branches each carry their own workflow file. Apply important workflow fixes in
the downstream repository and confirm that its release assets refresh there.
