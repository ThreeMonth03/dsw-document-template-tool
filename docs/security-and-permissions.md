# Security And Permissions

This document records which credentials are required and which publication
actions are intentionally manual.

## Current Policy

- Tool repo release assets use the built-in `GITHUB_TOKEN`.
- Translation repo release assets use the built-in `GITHUB_TOKEN`.
- depositar/DSW import is manual.
- No `DOCUMENT_TEMPLATE_PUBLISH_TOKEN` is required for the current workflow.

This keeps the translation process visible to maintainers without giving CI the
ability to publish directly into the public downstream source or DSW instance.

## GitHub Actions Permissions

Workflows that upload release assets need:

```yaml
permissions:
  contents: write
```

The workflow must pass the repository explicitly:

```shell
gh release upload "$release_tag" "$release_dir"/* \
  --repo "$GITHUB_REPOSITORY" \
  --clobber
```

Without `--repo`, `gh` may fail when the working directory is not the checked-out
repository root.

## Manual depositar Import

Manual import flow:

1. Download the versioned zip from the translation repo release.
2. Verify `SHA256SUMS`.
3. Import into the target DSW/depositar environment.
4. Render a representative project.

Do not store DSW admin credentials in this repo for routine releases.

## If Automatic Public Publishing Is Reintroduced

Before adding a token such as `DOCUMENT_TEMPLATE_PUBLISH_TOKEN`, decide:

- which repository or DSW instance the token can modify
- whether pushes go to draft/sync branches or directly to public default branch
- who can trigger the workflow
- whether fork PRs can access the secret
- how rollback works
- how release artifacts and public source branches stay traceable

Prefer a narrow token that can only push to the intended target repository. Do
not expose publication tokens to pull requests from forks.

## Sensitive Artifacts

Release assets and Actions artifacts should not include:

- real DSW user tokens
- private project answers
- private DSW API URLs unless intentionally public
- local machine paths that reveal secrets

The checked-in demo project should be synthetic or explicitly approved for
public CI artifacts.
