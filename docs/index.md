# DSW Document Template Tool

This Sphinx site documents maintainer workflows and stable Python modules used
by the DSW Science Europe document-template tooling and GitHub Actions
workflows.

Start with the operator quickstart when you are new to the codebase. Use the
package reference when checking maintainer-facing services, config models,
render helpers, and translation-tree APIs. Use the parser guide before changing
lower-level implementation details.

```{toctree}
:maxdepth: 2
:caption: Maintainer Docs

operator-quickstart
README
architecture
development-guidelines
command-reference
parser-and-translation-tree
version-upgrade-runbook
ci-and-release-runbook
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

api/template-transform
api/translation-tree
api/migration-and-config
api/render-and-regression
```
