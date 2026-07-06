# Configuration Reference

This page is the map for repository configuration files. Use it when a runbook
mentions a config path and you need to know whether that file is source,
generated output, workflow template, or downstream-only data.

All paths below are repository-relative references.

## Source Configs

| File | Owner | Purpose | Main Commands |
| --- | --- | --- | --- |
| `config/dsw-compat.yml` | Tool repo | Declares the proven DSW server, document worker, and `dsw-tdk` runtime for each supported template metamodel range. This is the source of truth for runtime matrix generation. | `make sync-dsw-runtime-matrix`, `make check-dsw-runtime-matrix`, `make discover-upstream-compat` |
| `config/regression.ci.yml` | Tool repo | Base CI regression template. Generated CI configs rewrite its baseline/candidate paths to the latest compatible built upstream workspace. | `make generate-regression-config`, `make render-regression-ci`, `make render-regression-ci-plan` |
| `config/regression.preview.yml` | Tool repo | Local preview regression config for a manually controlled DSW instance. It expects API token auth. | `make render-regression CONFIG=config/regression.preview.yml` |
| `config/regression.document.yml` | Tool repo | Released-template document regression config. Use it when both baseline and candidate are already installed in DSW and referenced by released template id. | `make render-regression CONFIG=config/regression.document.yml` |
| `config/requirements.txt` | Tool repo | Python, Sphinx, test, and DSW tooling dependencies for local and CI runs. | `make install-dev` |
| `config/ruff.toml` | Tool repo | Formatting and linting rules for Python source, scripts, tests, and Sphinx config. | `make format`, `make format-check`, `make lint` |

## Workflow and Stack Configs

| File | Owner | Purpose | Main Commands |
| --- | --- | --- | --- |
| `.github/workflows/headless_render_regression.yml` | Tool repo | Main CI workflow for checks, upstream discovery, clean scaffold artifacts, release assets, and DSW render regression. Its runtime matrix is generated from `config/dsw-compat.yml`. | `make check`, `make sync-dsw-runtime-matrix` |
| `.github/workflows/pages.yml` | Tool repo | GitHub Pages deployment for this documentation site. | `make docs` |
| `.github/dsw/docker-compose.yml` | Tool repo | Ephemeral DSW stack used by local and CI render tests. | `make start-ci-dsw`, `make stop-ci-dsw`, `make ci-dsw-logs` |
| `examples/github-actions/document_template_translation_sync.yml` | Tool repo example | Template workflow copied into downstream translation version branches. The sync script renders version-specific values from `translation-config.yml`. | `make sync-translation-version-branches` |

## Generated Configs

| Path | Created By | Purpose | Commit? |
| --- | --- | --- | --- |
| `config/.generated-regression.ci.yml` | `make generate-regression-config` or `make render-regression-ci` | Active single-version CI regression config. | No |
| `config/.generated-regression.ci.<metamodel>.<version>.<profile>.yml` | `make render-regression-ci-plan` | Per-version regression config generated from the compatibility ledger plan. | No |

Generated configs are ignored by git. If a generated config looks wrong, fix the
source config or generator instead of committing the generated file.

## Downstream Translation Config

The downstream translation repository owns `translation-config.yml`; this tool
only validates and consumes it. The schema is implemented by
`dsw_document_template_tool.translation_migration` and validated with:

```shell
make validate-translation-config TRANSLATION_REPO=/path/to/translation-repo
```

Important fields:

| Field | Meaning |
| --- | --- |
| `template.supported_versions` | Versions known to the translation control repo. A version can be known without being actively translated. |
| `version_policy` | Per-version lifecycle policy: whether automation may refresh, migrate into, or publish release assets. |
| `branches.control_branch` | Operations branch that owns repository-level config and docs. |
| `branches.version_branch_prefix` | Prefix for translator-facing branches, usually `translation/`. |
| `public_readme.path` | Canonical user-facing template README copied into generated version branches. |
| `publish.branch_prefix` | Branch prefix used when manually staging reviewed translated source for public handoff. |
| `xliff_exchange` | Optional XLIFF export/import settings. The default workflow still treats `translation.md` as canonical. |

Use [Downstream Integration](downstream-integration.md) for the operational
sequence and [Translation Workflow](translation-workflow.md) for translator-facing
behavior.
