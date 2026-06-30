# DSW Document Template Tool

Shared tooling for transforming, validating, translating, packaging, and
preview-rendering DSW document templates.

The current production use case is the Traditional Chinese translation workflow
for the Science Europe DMP Template. This repository is infrastructure focused:
it provides parser logic, CI helpers, compatibility checks, demo fixtures, and
release automation for clean upstream scaffolds.

## What This Repository Produces

| Output | Purpose |
| --- | --- |
| Parser, transform, migration, render, and CI helper code | Shared infrastructure for document-template translation workflows. |
| Clean scaffold release assets | Versioned upstream-derived workspaces, packages, checksums, and previews published from CI. |
| Demo KM/project fixtures | Stable inputs for local and CI render previews. |
| Example workflows and helper scripts | Reusable automation templates for repositories that consume the clean scaffold assets. |

Generated workspaces, generated packages, render outputs, and caches are build
artifacts. Keep them out of `master` unless a file is explicitly a reusable
fixture under `fixtures/`.

## First Five Minutes

For a local development sanity check:

```shell
make install-dev
make format-check
make lint
make test
```

For anything beyond that, start from the task map below. The root README is only
an entry point; operational detail lives in `docs/`.

## Start Here

If you are new to the project, start with the
[Documentation Index](docs/README.md). For common follow-up tasks:

| Task | Read |
| --- | --- |
| Day-to-day operation | [Operator Quickstart](docs/operator-quickstart.md) |
| Code layout and module ownership | [Architecture](docs/architecture.md) |
| Parser or translation tree changes | [Parser and Translation Tree](docs/parser-and-translation-tree.md) |
| CI, DSW, render, or release debugging | [Troubleshooting](docs/troubleshooting.md) |

## Version Support

The tooling supports Science Europe template versions from `v1.29.1` upward.
The DSW runtime matrix is declared in
[config/dsw-compat.yml](config/dsw-compat.yml).

On non-PR CI runs, this repository publishes clean scaffold prerelease assets
such as `clean-scaffold-dsw-science-europe-v1.30.1`. These are download buckets
for downstream maintenance, not finished translations. Their assets are
refreshed by CI; the Git tag commit is not the source of truth for generated
files.
