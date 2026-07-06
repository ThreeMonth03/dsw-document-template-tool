# Security and Permissions

This document records credentials and permissions required by this tooling
repository.

## Current Policy

- Tool repo clean scaffold release assets use the built-in `GITHUB_TOKEN`.
- Tool repo CI does not publish to public DSW instances or public translated
  template source repositories.
- No downstream publication token is required by this repo's normal workflow.
- Do not add tokens that let this repo push translated outputs to downstream
  repositories or DSW instances. Downstream repositories own that handoff.

Downstream translation repositories own their own publication, manual import,
and branch visibility policy. See
[Downstream Integration](downstream-integration.md) for the handoff boundary.

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

## Sensitive Artifacts

Release assets and Actions artifacts should not include:

- real DSW user tokens
- private project answers
- private DSW API URLs unless intentionally public
- local machine paths that reveal secrets

The checked-in demo project should be synthetic or explicitly approved for
public CI artifacts.
