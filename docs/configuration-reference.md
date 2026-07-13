# Configuration Reference

This page is the map for repository configuration files. Use it when a runbook
mentions a config path and you need to know whether that file is source,
generated output, workflow template, or public-repository data.

All paths below are repository-relative references.

## Source Configs

| File | Owner | Purpose | Main Commands |
| --- | --- | --- | --- |
| [`config/dsw-compat.yml`](../config/dsw-compat.yml) | Tool repo | Declares the proven DSW server, document worker, and `dsw-tdk` runtime for each supported template metamodel range. Its schema is strict: unknown fields and unsupported `schema_version` values fail validation. This is the source of truth for runtime matrix generation. | `make sync-dsw-runtime-matrix`, `make check-dsw-runtime-matrix`, `make discover-upstream-compat` |
| [`config/regression.ci.yml`](../config/regression.ci.yml) | Tool repo | Base CI regression template. Generated CI configs rewrite its baseline/candidate paths to the latest compatible built upstream workspace. | `make generate-regression-config`, `make render-regression-ci`, `make render-regression-ci-plan` |
| [`config/regression.preview.yml`](../config/regression.preview.yml) | Tool repo | Local preview regression config for a manually controlled DSW instance. It expects API token auth. | `make render-regression CONFIG=config/regression.preview.yml` |
| [`config/regression.document.yml`](../config/regression.document.yml) | Tool repo | Released-template document regression config. Use it when both baseline and candidate are already installed in DSW and referenced by released template id. | `make render-regression CONFIG=config/regression.document.yml` |
| [`pyproject.toml`](../pyproject.toml) | Tool repo | Python package metadata, dependencies, development extras, and installed `dsw-template-*` console scripts. | `make install-dev` |
| [`config/ruff.toml`](../config/ruff.toml) | Tool repo | Formatting and linting rules for Python source, scripts, tests, and Sphinx config. | `make format`, `make format-check`, `make lint` |

## Workflow and Stack Configs

| File | Owner | Purpose | Main Commands |
| --- | --- | --- | --- |
| [`.github/workflows/headless_render_regression.yml`](../.github/workflows/headless_render_regression.yml) | Tool repo | Main CI workflow for checks, upstream discovery, clean scaffold artifacts, release assets, and DSW render regression. Its runtime matrix is generated from [`config/dsw-compat.yml`](../config/dsw-compat.yml). | `make check`, `make sync-dsw-runtime-matrix` |
| [`.github/workflows/pages.yml`](../.github/workflows/pages.yml) | Tool repo | GitHub Pages deployment for this documentation site. | `make docs` |
| [`.github/dsw/docker-compose.yml`](../.github/dsw/docker-compose.yml) | Tool repo | Ephemeral DSW stack used by local and CI render tests. | `make start-ci-dsw`, `make stop-ci-dsw`, `make ci-dsw-logs` |
| [`examples/github-actions/document_template_translation_sync.yml`](../examples/github-actions/document_template_translation_sync.yml) | Tool repo example | Template workflow copied into public repository `sync/v*` branches. The sync script renders version-specific values from `translation-config.yml`. | `make sync-translation-version-branches` |
| [`examples/translation-repository/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples/translation-repository) | Tool repo example | Copy-ready README and docs templates for the public translated-template repository. Active public-repository copies are repository-owned. | Manual copy after `make docs` |

## Generated Configs

| Path | Created By | Purpose | Commit? |
| --- | --- | --- | --- |
| `config/.generated-regression.ci.yml` | `make generate-regression-config` or `make render-regression-ci` | Active single-version CI regression config. | No |
| `config/.generated-regression.ci.<metamodel>.<version>.<profile>.yml` | `make render-regression-ci-plan` | Per-version regression config generated from the compatibility ledger plan. | No |

Generated configs are ignored by git. If a generated config looks wrong, fix the
source config or generator instead of committing the generated file.

## Public Repository Translation Config

The public translated-template repository owns `translation-config.yml`; this
tool only validates and consumes it. The schema is implemented by
`dsw_document_template_tool.translation_migration` and validated with:

```shell
make validate-translation-config TRANSLATION_REPO=/path/to/science-europe-template-zh_Hant
```

The current schema is `schema_version: 2`. Validation rejects unknown fields so
misspellings and retired settings cannot remain as inert configuration.

Important fields:

| Field | Meaning |
| --- | --- |
| `template.supported_versions` | Upstream versions known to the public repository. A version can be known without being actively translated. |
| `translation.translated_template_*` | Public DSW metadata written to `template.json`, including organization id, template id, name, and optional description. |
| `version_policy` | Per-version lifecycle policy: whether automation may refresh, migrate into, or publish release assets. |
| `branches.control_branch` | Operations branch that owns repository-level config and docs. |
| `branches.version_branch_prefix` | Prefix for translator-facing branches, usually `sync/`. |
| `public_readme.path` | Canonical user-facing template README copied into generated version branches. |
| `xliff_exchange` | Optional XLIFF export/import settings. The default workflow still treats `translation.md` as canonical. |

### Common Version Policy Snippets

Use these snippets under `version_policy.overrides` when a version needs an
explicit lifecycle. The default policy should usually stay scaffold-only, so new
upstream tags do not silently become translation work.

Scaffold exists, but translation has not started:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: available
      refresh: false
      migrate_into: false
      publish_release: false
      reason: scaffold available; translation not started
```

Actively translated and allowed to update automatically:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: active
      refresh: artifact
      migrate_into: auto
      publish_release: true
      reason: actively translated
```

Maintenance branch that can be refreshed only by an operator:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: maintenance
      refresh: manual
      migrate_into: manual
      publish_release: true
      reason: maintenance changes require operator action
```

Published and frozen:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: published
      refresh: false
      migrate_into: false
      publish_release: true
      reason: published; do not rebuild from newer scaffold artifacts
```

Archived and fully frozen:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: archived
      refresh: false
      migrate_into: false
      publish_release: false
      reason: archived; keep historical branch and release assets unchanged
```

`refresh` controls whether `sync/v*` branches are created or refreshed.
`migrate_into` controls whether translations from another version may be merged
into this version. `publish_release` controls translated release asset
generation. `state` and `reason` are maintainer-facing labels that make CI
summaries and reviews easier to understand.

Use `refresh: artifact` only for versions that should be rebuilt from the latest
tooling clean scaffold artifact. Published and archived versions must use
`refresh: false`; the loader rejects frozen versions that could still mutate
from artifact refreshes.

Use [Public Template Repository Integration](downstream-integration.md) for the
operational sequence and [Translation Workflow](translation-workflow.md) for
translator-facing behavior.
