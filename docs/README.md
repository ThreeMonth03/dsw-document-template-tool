# Documentation Index

Use this directory as the maintenance manual for the document-template tooling.
The root `README.md` is only an entry point; operational detail should live
here.

## Start Here

Choose the path closest to your task:

- First-time maintainer: [Operator Quickstart](operator-quickstart.md).
- Codebase orientation: [Architecture](architecture.md).
- Parser or translation-tree changes:
  [Parser and Translation Tree](parser-and-translation-tree.md).
- New upstream tag or metamodel:
  [Version Upgrade Runbook](version-upgrade-runbook.md).
- CI, DSW, render, or release debugging:
  [CI and Release Runbook](ci-and-release-runbook.md) and
  [Troubleshooting](troubleshooting.md).
- Downstream translation repository integration:
  [Downstream Integration](downstream-integration.md).
- Final scaffold artifact review: [QA Checklist](qa-checklist.md).

## Reference

- [Development Guidelines](development-guidelines.md) defines code review and
  maintenance expectations.
- [Configuration Reference](configuration-reference.md) explains source configs
  and generated config boundaries.
- [Command Reference](command-reference.md) lists Make targets, required
  variables, and helper scripts.
- [DSW Compatibility Probe](compatibility/dsw-compatibility-probe.md) explains
  the unsupported metamodel follow-up PR.
- [Security and Permissions](security-and-permissions.md) covers tokens,
  permissions, and publication boundaries.

## Workflow Documents

- [Translation Workflow](translation-workflow.md) explains the path from
  upstream template source to translator-facing Markdown and packageable
  translated template.
- [Regression Workflow](regression-workflow.md) explains how local and CI
  render checks prove that generated templates still behave correctly.

## Documentation Rules

- Keep the root `README.md` short and navigational.
- Put durable procedures in runbooks, not in GitHub Actions comments.
- When adding a new CI helper, document both the command and the failure mode it
  is meant to prevent.
- If a behavior depends on GitHub semantics, such as scheduled workflows or
  release asset overwrites, state that explicitly.
