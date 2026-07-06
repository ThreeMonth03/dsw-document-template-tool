# Security and Permissions

Use this page when configuring GitHub Actions, secrets, and publication policy
for this translation repository.

## Visibility

Repository visibility controls who can see translation work:

- public repository: draft translation branches, PRs, logs, artifacts, and
  releases may be visible publicly;
- private repository: translation work is hidden from the public, but any public
  handoff branch or release asset should be treated as published output.

If translation drafts must stay private, do not push `translation/v*` branches
to a public remote.

## Workflow Permissions

Typical permissions:

| Workflow | Permission | Writes |
| --- | --- | --- |
| Operations sync | `contents: write`, `pull-requests: write`, `actions: read` | config updates, version branches, migration PRs |
| Version branch validation | `contents: write`, `actions: write`, `statuses: write` | generated repair commits, release assets, status marker |

Use the built-in `GITHUB_TOKEN` where possible. Use a separate automation token
only when the workflow must update workflow files or cross repository
boundaries.

## Sensitive Artifacts

Do not commit or upload:

- real DSW user tokens;
- private project answers;
- private DSW API URLs unless intentionally public;
- local machine paths that reveal secrets.

Demo project fixtures should be synthetic or explicitly approved for public CI
artifacts.
