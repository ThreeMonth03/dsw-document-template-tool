# Documentation Index

Use this directory as the maintenance manual for the template tooling. The top
level `README.md` is only an entry point; operational detail should live here.

## If You Need to...

| Task | Read |
| --- | --- |
| Take over day-to-day operation | [Operator Quickstart](operator-quickstart.md) |
| Understand the repo layout and module responsibilities | [Architecture](architecture.md) |
| Change code safely | [Development Guidelines](development-guidelines.md) |
| Find a Make target or helper script | [Command Reference](command-reference.md) |
| Modify parsing, markers, translation tree export, merge, or sync behavior | [Parser and Translation Tree](parser-and-translation-tree.md) |
| Handle a new upstream Science Europe tag or metamodel | [Version Upgrade Runbook](version-upgrade-runbook.md) |
| Debug CI, clean scaffold release assets, or DSW previews | [CI and Release Runbook](ci-and-release-runbook.md) and [Troubleshooting](troubleshooting.md) |
| Connect a translation repository to clean scaffold artifacts | [Downstream Integration](downstream-integration.md) |
| Validate tool-generated scaffold artifacts | [QA Checklist](qa-checklist.md) |
| Review tokens, permissions, and publication boundaries | [Security and Permissions](security-and-permissions.md) |

## Workflow Documents

- [Translation Workflow](translation-workflow.md) explains the high-level path
  from upstream template source to translator-facing Markdown and packageable
  translated template, including optional XLIFF exchange for external editing
  interfaces.
- [Regression Workflow](regression-workflow.md) explains how the local and CI
  render checks prove that generated templates still behave correctly.

## Documentation Rules

- Keep the root `README.md` short and navigational.
- Put durable procedures in runbooks, not in GitHub Actions comments.
- When adding a new CI helper, document both the command and the failure mode it
  is meant to prevent.
- If a behavior depends on GitHub semantics, such as scheduled workflows or
  release asset overwrites, state that explicitly.
