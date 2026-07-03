# Security and Permissions

This document records credentials and permissions required by this tooling
repository.

## Current Policy

- Tool repo clean scaffold release assets use the built-in `GITHUB_TOKEN`.
- Tool repo CI does not publish to public DSW instances or public translated
  template source repositories.
- No downstream publication token is required by this repo's normal workflow.

Downstream translation repositories own their own publication and manual import
policy.

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

## If Automatic Downstream Publishing Is Reintroduced

Before adding any token that can push to another repository or DSW instance,
decide:

- which repository or DSW instance the token can modify
- whether pushes go to draft/sync branches or directly to public default branch
- who can trigger the workflow
- whether fork PRs can access the secret
- how rollback works
- how release artifacts and public source branches stay traceable

Prefer a narrow token that can only push to the intended target repository. Do
not expose publication tokens to pull requests from forks. Document the final
policy in the downstream repository as well.

## Sensitive Artifacts

Release assets and Actions artifacts should not include:

- real DSW user tokens
- private project answers
- private DSW API URLs unless intentionally public
- local machine paths that reveal secrets

The checked-in demo project should be synthetic or explicitly approved for
public CI artifacts.
