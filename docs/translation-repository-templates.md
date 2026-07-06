# Translation Repository Templates

Use this page when creating or refreshing documentation in a downstream
document-template translation repository.

The copy-ready templates live in:

```text
examples/translation-repository/
```

They are intentionally generic. Copy them into the downstream repository, then
edit repository names, branch names, and publication policy there. The tool repo
is the template source; the downstream repository is the source of truth for its
actual operations.

## What to Copy

Recommended starting set:

- [`examples/translation-repository/README.md`](https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/examples/translation-repository/README.md)
- [`examples/translation-repository/docs/README.md`](https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/examples/translation-repository/docs/README.md)
- [`examples/translation-repository/docs/branch-policy.md`](https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/examples/translation-repository/docs/branch-policy.md)
- [`examples/translation-repository/docs/maintenance-runbook.md`](https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/examples/translation-repository/docs/maintenance-runbook.md)
- [`examples/translation-repository/docs/security-and-permissions.md`](https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/examples/translation-repository/docs/security-and-permissions.md)

Copy workflow templates separately from
[`examples/github-actions/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples/github-actions).
The docs templates explain the expected branch model; the workflow templates
implement the version-branch validation and packaging flow.

## Public Visibility Policy

Do not describe a downstream repository as "private" or "public" in the tool
repo docs unless that is a project decision. The safe general rule is:

- public repositories make `translation/v*` branches, pull requests, logs,
  Actions artifacts, and release assets visible to anyone who can view the
  repository;
- private repositories keep that work hidden from the public, but public release
  or sync branches must still be treated as public deliverables;
- if translation drafts must remain private, do not push draft
  `translation/v*` branches to a public remote;
- if a single public repository is used for both work and publish handoff,
  expect translation drafts to be visible.

The supported integrated layout is branch-based separation:

| Branch or asset | Purpose |
| --- | --- |
| `master` or another operations branch | Repository-level config, workflows, and docs. |
| `translation/v*` | Translator-facing workspaces and review PRs. |
| `sync/v*` or the configured handoff branch prefix | Clean translated template source for handoff. |
| release assets | Package zip, preview PDF, checksums, and notes. |

This layout reduces repository count, but it does not hide work-in-progress
translation branches if the repository is public.

## Update Rule

When these templates change:

1. Update `examples/translation-repository/` in this tool repo.
2. Run `make check` and `make docs`.
3. Copy the reviewed template changes into downstream translation repositories
   that want the new wording.
4. Do not assume updating this tool repo rewrites downstream docs automatically.

This mirrors the KM translation tool pattern: reusable docs live with the tool,
while production translation repositories copy and own their active copies.
