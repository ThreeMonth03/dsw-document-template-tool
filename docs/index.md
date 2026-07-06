# DSW Document Template Tool

This site documents the tooling used to transform upstream DSW document
templates into clean scaffold artifacts for translation repositories.

The current production workflow supports the Traditional Chinese Science
Europe DMP Template translation. This repository owns parser behavior,
translation-tree generation, scaffold packaging, render regression, and release
asset automation. It does not own the translated content itself.

## Start Here

Choose the path closest to what you are doing:

- New to the repository: read the [Operator Quickstart](operator-quickstart.md)
  first. It explains the mental model, safe commands, and normal maintenance
  flow.
- Handling a new upstream Science Europe tag: use the
  [Version Upgrade Runbook](version-upgrade-runbook.md), then verify release
  assets with the [QA Checklist](qa-checklist.md).
- Debugging CI, DSW, render previews, or release upload: start with the
  [CI and Release Runbook](ci-and-release-runbook.md), then use
  [Troubleshooting](troubleshooting.md) for failure modes.
- Changing parser, marker, translation tree, migration, or sync behavior: read
  [Architecture](architecture.md), then follow
  [Parser and Translation Tree](parser-and-translation-tree.md).
- Connecting a downstream translation repository: use
  [Downstream Integration](downstream-integration.md).
- Finding commands: use the [Command Reference](command-reference.md) for Make
  targets, required variables, and lower-level helper scripts.

## Package Reference

Use these pages when checking maintainer-facing Python interfaces, shared data
contracts, render helpers, or translation-tree APIs:

- [Template Transform Reference](api/template-transform.rst)
- [Translation Tree Reference](api/translation-tree.rst)
- [Migration and Config Reference](api/migration-and-config.rst)
- [Render and Regression Reference](api/render-and-regression.rst)

For implementation helpers below these facades, use
[Architecture](architecture.md) to find the owning module and tests.

```{toctree}
:maxdepth: 2
:caption: Maintainer Docs
:hidden:

operator-quickstart
architecture
development-guidelines
internal-change-guide
configuration-reference
command-reference
parser-and-translation-tree
version-upgrade-runbook
ci-and-release-runbook
compatibility/dsw-compatibility-probe
downstream-integration
regression-workflow
translation-workflow
qa-checklist
troubleshooting
security-and-permissions
```

```{toctree}
:maxdepth: 2
:caption: Package Reference
:hidden:

api/template-transform
api/translation-tree
api/migration-and-config
api/render-and-regression
```
