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

## Policy Source

Keep the branch layout and visibility rules in one place:
[Downstream Integration](downstream-integration.md). The templates listed above
are starting files for the downstream repository; they should not become a
second copy of the policy in this tool repo.

## Update Rule

When these templates change:

1. Update `examples/translation-repository/` in this tool repo.
2. Run `make check` and `make docs`.
3. Copy the reviewed template changes into downstream translation repositories
   that want the new wording.
4. Do not assume updating this tool repo rewrites downstream docs automatically.

This mirrors the KM translation tool pattern: reusable docs live with the tool,
while production translation repositories copy and own their active copies.
