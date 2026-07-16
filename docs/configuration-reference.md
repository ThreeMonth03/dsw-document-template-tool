# Configuration Reference

This page is the map for repository configuration files. Use it when a runbook
mentions a config path and you need to know whether that file is source,
generated output, workflow template, or public-repository data.

All paths below are repository-relative references.

## Source Configs

| File | Owner | Purpose | Main Commands |
| --- | --- | --- | --- |
| [`config/dsw-compat.yml`](../config/dsw-compat.yml) | Tool repo | Declares the proven DSW server, document worker, and `dsw-tdk` runtime for each supported template metamodel range. Its schema is strict: duplicate keys, unknown fields, and unsupported `schema_version` values fail validation. This is the source of truth for runtime matrix generation. | `make sync-dsw-runtime-matrix`, `make check-dsw-runtime-matrix`, `make discover-upstream-compat` |
| [`config/regression.ci.yml`](../config/regression.ci.yml) | Tool repo | Base complete-fixture regression template. Upstream config generation writes an equality comparison; translated-package config generation writes a single-package render assertion. | `make generate-regression-config`, `make render-regression-ci-plan`, `make render-translated-package-regression` |
| [`config/regression-evidence.yml`](../config/regression-evidence.yml) | Tool repo | Pins immutable Knowledge Model provenance and assigns one fixture to every DSW runtime. Config generation verifies its checksum and package metadata before DSW starts; the final evidence gate combines it with regression, coverage, and PDF results. | `make generate-regression-config`, `make render-regression-ci-plan`, `make verify-runtime-evidence` |
| [`config/regression.preview.yml`](../config/regression.preview.yml) | Tool repo | Local preview regression config for a manually controlled DSW instance. It expects API token auth. | `make render-regression CONFIG=config/regression.preview.yml` |
| [`config/regression.document.yml`](../config/regression.document.yml) | Tool repo | Released-template document regression config. Use it when both baseline and candidate are already installed in DSW and referenced by released template id. | `make render-regression CONFIG=config/regression.document.yml` |
| [`pyproject.toml`](../pyproject.toml) | Tool repo | Python package metadata, dependencies, development extras, and installed `dsw-template-*` console scripts. | `make install-dev` |
| [`config/ruff.toml`](../config/ruff.toml) | Tool repo | Formatting and linting rules for Python source, scripts, tests, and Sphinx config. | `make format`, `make format-check`, `make lint` |

The three regression configs use the strict loader in
[`yaml_config.py`](../src/dsw_document_template_tool/yaml_config.py). Duplicate
or unknown fields fail before a DSW request runs, so a misspelled option cannot
silently fall back to its default.

`regression.assertion` is either `equal` or `render_success`. Equality requires
baseline and candidate subjects. Render success rejects a baseline and is used
with a `local_package` candidate so translated-package CI validates the actual
ZIP without a meaningless cross-language or self-comparison.

`generated_fixtures` in [`config/regression.ci.yml`](../config/regression.ci.yml)
uses these coverage controls:

| Field | Meaning |
| --- | --- |
| `count` | Maximum number of selected cases that may become DSW projects and render comparisons. |
| `selection_pool_size` | Number of deterministic candidates evaluated locally before selecting cases. It must be at least `count`. |
| `require_complete_coverage` | Fail when the selected cases do not cover every reachable answer and supported collection shape. CI keeps this enabled for every planned version. |

Increase `selection_pool_size` before increasing `count`: searching more local
candidates is much cheaper than rendering more DSW projects.

`config/regression-evidence.yml` deliberately separates document-template and
Knowledge Model metamodels. Each `runtime_knowledge_models` key must match a
`metamodel_key` in `config/dsw-compat.yml`. A Knowledge Model entry records:

- repository-relative bundle path
- exact DSW package ID and version
- Knowledge Model `metamodelVersion`
- authoritative source URL
- lowercase SHA-256 checksum

Adding a runtime without an assignment, replacing a bundle without updating its
checksum, or declaring metadata that differs from the bundle fails before any
render work begins.

The compatibility probe may update only the assignment lines between the
`BEGIN/END GENERATED RUNTIME KNOWLEDGE MODEL ASSIGNMENTS` comments. For a new
metamodel it copies the closest previous runtime's pinned fixture as a testable
assumption. The `knowledge_models` catalog, provenance, and checksums remain
maintainer-owned and are never invented by automation.

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
| `config/.generated-regression.ci.<metamodel>.<version>.yml` | `make render-regression-ci-plan` | Per-version regression config generated from the compatibility ledger plan. | No |
| `config/.generated-regression.translated.yml` | `make render-translated-package-regression` | Single-package full render config using the pinned KM for the package metamodel. | No |
| `outputs/runtime-evidence/<metamodel>/evidence.json` and `evidence.md` | `make verify-runtime-evidence` | Runtime, KM provenance, complete branch coverage, regression result, and strict PDF proof for every planned version. | No |

Generated configs are ignored by git. If a generated config looks wrong, fix the
source config or generator instead of committing the generated file.

## Public Repository Translation Config

The public translated-template repository owns `translation-config.yml`; this
tool only validates and consumes it. The schema is implemented by
`dsw_document_template_tool.translation_repository` and validated with:

```shell
make validate-translation-config TRANSLATION_REPO=/path/to/science-europe-template-zh_Hant
```

The current schema is `schema_version: 2`. Validation rejects duplicate and
unknown fields so ambiguous values, misspellings, and retired settings cannot
remain as inert configuration.

Important fields:

| Field | Meaning |
| --- | --- |
| `template.supported_versions` | Upstream versions known to the public repository. A version can be known without being actively translated. |
| `translation.translated_template_*` | Public DSW metadata written to `template.json`, including organization id, template id, name, and optional description. |
| `version_policy` | Per-version lifecycle policy: whether automation may refresh, migrate into, or publish release assets. |
| `branches.control_branch` | Operations branch that owns repository-level config and docs. |
| `branches.version_branch_prefix` | Prefix for translator-facing branches, usually `sync/`. |
| `tooling.repository` / `tooling.ref` | Tool repository and revision used by public-repository workflows. Keep both as one-line YAML scalars: operations needs them before it can check out the tool and run full config validation. |
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
`migrate_into` controls cross-version synchronization membership. `auto`
versions may act as source and target during normal fan-out, `manual` versions
participate only when explicitly selected by an operator, and `false` versions
do not participate. For an allowed target, blank units are filled and existing
translations are updated only when the source structure is identical.
`publish_release` controls translated release asset generation. `state` and
`reason` are maintainer-facing labels that make CI summaries and reviews easier
to understand.

`state` must be one of `available`, `active`, `maintenance`, `published`, or
`archived`. Validation rejects spelling variants rather than treating them as a
new state with undefined lifecycle behavior.

Policy precedence is `defaults`, then matching `rules` in file order, then the
exact version `override`. Rules and overrides change only fields they explicitly
declare; omitted fields keep the value inherited from the previous layer. Use
the domain values `artifact` and `auto` when enabling automation. The ambiguous
shortcuts `refresh: true` and `migrate_into: true` are rejected.

Use `refresh: artifact` only for versions that should be rebuilt from the latest
tooling clean scaffold artifact. Published and archived versions must use both
`refresh: false` and `migrate_into: false`; the loader rejects frozen versions
that could still mutate from artifact refreshes or cross-version sync.

Use [Public Template Repository Integration](downstream-integration.md) for the
operational sequence and [Translation Workflow](translation-workflow.md) for
translator-facing behavior.
