# DSW Document Template Tool

Shared tooling for transforming, validating, translating, packaging, and
preview-rendering DSW document templates.

The current production use case is the Traditional Chinese translation of the
Science Europe DMP Template. The repository is intentionally infrastructure
focused: it owns parser logic, CI helpers, compatibility checks, demo fixtures,
and release automation. It does not own the final public translated template
source.

## Repository Roles

- `ThreeMonth03/DSW-document-template-tool`: shared tooling, tests, clean
  upstream scaffolds, fixture projects, and CI helpers.
- Downstream translation repositories: own translator-facing version branches,
  translated release assets, and public import or publication policy.

Generated workspaces, generated packages, render outputs, and caches are build
artifacts. Keep them out of `master` unless a file is explicitly a reusable
fixture under `workspace/`.

## Quick Start

```shell
make install-dev
make format-check
make lint
make test
```

Run a local DSW render regression:

```shell
make start-ci-dsw
make render-regression-ci
make stop-ci-dsw
```

Build clean upstream scaffold artifacts:

```shell
make discover-upstream-compat
make build-upstream-artifacts
make render-upstream-artifact-previews
```

## Common Tasks

- Change parser or tree logic: read
  [Parser and Translation Tree](docs/parser-and-translation-tree.md).
- Take over routine operations: read
  [Operator Quickstart](docs/operator-quickstart.md).
- Handle a new upstream template tag: read
  [Version Upgrade Runbook](docs/version-upgrade-runbook.md).
- Debug GitHub Actions, DSW, release assets, or render failures: read
  [Troubleshooting](docs/troubleshooting.md).
- Publish reviewed translated source manually: read
  [CI and Release Runbook](docs/ci-and-release-runbook.md).
- Find a command quickly: read
  [Command Reference](docs/command-reference.md).

## Documentation

Start with the [Documentation Index](docs/README.md). The most important
maintenance documents are:

- [Architecture](docs/architecture.md)
- [Operator Quickstart](docs/operator-quickstart.md)
- [Development Guidelines](docs/development-guidelines.md)
- [Translation Workflow](docs/translation-workflow.md)
- [Regression Workflow](docs/regression-workflow.md)
- [Downstream Integration](docs/downstream-integration.md)
- [QA Checklist](docs/qa-checklist.md)
- [Security and Permissions](docs/security-and-permissions.md)

## Version and Release Policy

The tooling supports Science Europe template versions from `v1.29.1` upward.
The DSW runtime matrix is declared in
[config/dsw-compat.yml](config/dsw-compat.yml).

On non-PR CI runs, the tool repo publishes clean scaffold prerelease assets such
as `clean-scaffold-dsw-science-europe-v1.30.1`. These releases are download
buckets for downstream maintenance. Their assets are refreshed by CI; the Git
tag itself is not the source of truth for the generated files.

Downstream translation repositories consume these scaffold releases and publish
their own translated packages.
