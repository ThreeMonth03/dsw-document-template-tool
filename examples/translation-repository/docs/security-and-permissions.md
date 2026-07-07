# Security and Permissions

Use this page when configuring GitHub Actions, secrets, and publication policy
for this translation repository.

## Visibility

Use [Branch Policy](branch-policy.md) for repository visibility and branch
separation rules. This page focuses on workflow permissions and sensitive
artifacts.

## Workflow Permissions

Typical permissions:

| Workflow | Permission | Writes |
| --- | --- | --- |
| Operations sync | `contents: write`, `pull-requests: write`, `actions: read` | config updates, version branches, migration PRs |
| Version branch validation | `contents: write`, `actions: write`, `statuses: write` | generated repair commits, release assets, status marker |

Use the built-in `GITHUB_TOKEN` where possible. Use a separate automation token
only when the workflow must update workflow files or cross repository
boundaries.

## Workflow Synchronization Token

Operations sync can refresh normal branch content with the built-in token. It
needs a token with workflow permission only when it must update generated files
under `.github/workflows/` on `sync/v*` branches.

Use a repository-limited token when possible:

- fine-grained PAT: `Contents: Read and write`, `Workflows: Read and write`
- classic PAT: `repo`, `workflow`

Set the token as `TRANSLATION_AUTOMATION_TOKEN` without printing it:

```shell
gh auth refresh -h github.com -s repo -s workflow
gh auth token | gh secret set TRANSLATION_AUTOMATION_TOKEN \
  --repo OWNER/REPOSITORY
```

Then rerun the operations workflow. With this secret present, operations sync
may pass `--sync-workflows` and regenerate version-branch workflow files from
the tool repository template.

## Sensitive Artifacts

Do not commit or upload:

- real DSW user tokens;
- private project answers;
- private DSW API URLs unless intentionally public;
- local machine paths that reveal secrets.

Demo project fixtures should be synthetic or explicitly approved for public CI
artifacts.
