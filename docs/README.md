# Documentation Index

Use this directory as the maintenance manual for the template tooling. The top
level `README.md` is only an entry point; operational detail should live here.

## If You Need To...

| Task | Read |
| --- | --- |
| Understand the repo layout and module responsibilities | [Architecture](architecture.md) |
| Change code safely | [Development Guidelines](development-guidelines.md) |
| Find a Make target or helper script | [Command Reference](command-reference.md) |
| Modify parsing, markers, translation tree export, merge, or sync behavior | [Parser And Translation Tree](parser-and-translation-tree.md) |
| Handle a new upstream Science Europe tag or metamodel | [Version Upgrade Runbook](version-upgrade-runbook.md) |
| Debug CI, release assets, DSW previews, or manual publishing | [CI And Release Runbook](ci-and-release-runbook.md) and [Troubleshooting](troubleshooting.md) |
| Maintain the downstream translation repository | [Downstream Translation Repo](downstream-translation-repo.md) |
| Validate a package before import | [QA Checklist](qa-checklist.md) |
| Review tokens, permissions, and publication boundaries | [Security And Permissions](security-and-permissions.md) |

## Workflow Documents

- [Translation Workflow](translation-workflow.md) explains the high-level path
  from upstream template source to translator-facing Markdown and packageable
  translated template.
- [Regression Workflow](regression-workflow.md) explains how the local and CI
  render checks prove that generated templates still behave correctly.
- [Maintenance Guide](maintenance.md) is a compact checklist-oriented guide; use
  the more focused runbooks above for detailed procedures.

## Documentation Rules

- Keep the root `README.md` short and navigational.
- Put durable procedures in runbooks, not in GitHub Actions comments.
- When adding a new CI helper, document both the command and the failure mode it
  is meant to prevent.
- If a behavior depends on GitHub semantics, such as scheduled workflows or
  release asset overwrites, state that explicitly.
