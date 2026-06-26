# DSW Document Template Tool

This repository contains the shared infrastructure for validating and
translating DSW document templates. It is intentionally a tooling repo: it owns
the parser, template transforms, regression checks, fixture project, CI helpers,
and packaging workflow. It does not own the finished public translated template.

The current production use case is the Traditional Chinese translation of the
Science Europe DMP Template, but the code is organized so future template
versions and downstream translation repositories can reuse the same pipeline.

## Repository Roles

There are three repositories in the workflow:

- `ThreeMonth03/DSW-document-template-tool`: shared tooling, tests, clean
  upstream scaffolds, demo project fixtures, and CI helpers.
- `ThreeMonth03/DSW-document-template-translation`: translation control repo
  with one `translation/v*` branch per supported upstream template version.
- `depositar/science-europe-template-zh_Hant`: public downstream template source,
  updated manually only after generated artifacts are reviewed.

Generated workspaces and PDFs are build artifacts. Keep them out of `master`
unless a file is explicitly a small reusable fixture under `workspace/`.

## What Gets Committed

Committed source:

- `src/`: reusable Python package and CLI entrypoints
- `scripts/ci/`: GitHub Actions helpers used by downstream repos
- `config/`: regression and DSW compatibility configuration
- `examples/`: copy-paste workflow templates
- `workspace/knowledge-models/`: checked-in demo KM bundles
- `workspace/projects/`: checked-in demo project references and events
- `assets/fonts/`: shared fonts used by generated translated templates

Ignored generated files:

- `outputs/`
- `.cache/`
- `workspace/document-templates/`
- Python caches and local virtualenvs

## Quick Start

Install the local development environment:

```shell
make install-dev
```

Run the full local test suite:

```shell
make test
```

Run formatting and lint checks:

```shell
make format-check
make lint
```

Start the local DSW stack and run render regression:

```shell
make start-ci-dsw
make render-regression-ci
make stop-ci-dsw
```

## Main Workflows

Translation scaffolding:

```shell
make transform
make export-translation-tree
make merge-translation-tree
make sync-translation-tree
```

Upstream version artifact generation:

```shell
make discover-upstream-compat
make build-upstream-artifacts
make render-upstream-artifact-previews
```

Manual public publishing after review:

```shell
make publish-translated-template \
  TRANSLATION_REPO=/path/to/DSW-document-template-translation \
  PUBLISH_VERSION=v1.30.1
```

## Documentation

Use these docs instead of reverse-engineering the Makefile:

- [Translation Workflow](docs/translation-workflow.md): compact/expanded trees,
  translator-facing files, migration, and publishing.
- [Regression Workflow](docs/regression-workflow.md): fixture projects,
  headless DSW regression, upstream artifacts, and CI matrix behavior.
- [Maintenance Guide](docs/maintenance.md): repository boundaries, generated
  files, CI helpers, compatibility updates, and common checks.

## Current Version Policy

The tooling supports Science Europe template versions from `v1.29.1` upward.
The DSW runtime matrix is declared in [config/dsw-compat.yml](config/dsw-compat.yml).
When upstream releases a new tag, CI discovers whether an existing runtime can
handle it. If a new `metamodelVersion` appears, CI reads the official DSW
document-template metamodel notes and suggests the minimum DSW version to test.
Add a runtime only after smoke-testing the matching DSW and TDK versions.

## Design Principles

- Keep translator files readable: source sentence first, editable translation
  block second, machine metadata out of the way.
- Keep generated outputs reproducible: CI artifacts are preferred over checked-in
  `outputs/`.
- Keep migration conservative: only exact-safe translations are copied across
  versions automatically.
- Keep YAML thin: workflow logic belongs in tested Python helpers whenever it
  has branching, parsing, or cross-repository behavior.
