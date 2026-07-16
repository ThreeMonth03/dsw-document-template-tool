SHELL := bash

# Keep user-overridable defaults in lexicographic order; tests enforce this so
# CI/maintenance knobs stay easy to scan.
BOOTSTRAP_PYTHON ?= python3
CI_CONFIG ?= config/regression.ci.yml
CLEAN_SCAFFOLD_ARTIFACT_BRANCH ?= master
CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR ?= outputs/downloaded-clean-scaffolds
CLEAN_SCAFFOLD_ARTIFACT_RUN_ID ?=
CLEAN_SCAFFOLD_ARTIFACT_WORKFLOW ?= headless_render_regression.yml
CLEAN_SCAFFOLD_RELEASE_COMMIT_SHA ?= $(shell git rev-parse HEAD)
CLEAN_SCAFFOLD_RELEASE_DRY_RUN ?= true
CLEAN_SCAFFOLD_RELEASE_ROOT ?= outputs/release-assets/clean-scaffold
COMPACT_TEMPLATE_DIR ?= workspace/document-templates/compact/$(WORKSPACE_TEMPLATE_NAME)
COMPAT_LEDGER_DIR ?= outputs/compat-ledger/$(SOURCE_TEMPLATE_ID)
COMPAT_PROBE_BASE_BRANCH ?= master
COMPAT_PROBE_DRY_RUN ?= true
COMPAT_PROBE_REPORT ?= outputs/upstream-compat/discovery.md
COMPAT_PROBE_REPORT_PATH ?= docs/compatibility/dsw-compatibility-probe.md
CONFIG ?= config/regression.preview.yml
DOCS_BUILD_DIR ?= docs/_build/html
DOCS_SOURCE_DIR ?= docs
DSW_COMPAT_CONFIG ?= config/dsw-compat.yml
DSW_TDK ?= $(VENV_DIR)/bin/dsw-tdk
DSW_TEMPLATE_RENDER_PROJECT ?= $(VENV_DIR)/bin/dsw-template-render-project
DSW_TEMPLATE_RENDER_REGRESSION ?= $(VENV_DIR)/bin/dsw-template-render-regression
DSW_TEMPLATE_TRANSFORM ?= $(VENV_DIR)/bin/dsw-template-transform
DSW_TEMPLATE_TREE ?= $(VENV_DIR)/bin/dsw-template-tree
EXPANDED_TEMPLATE_DIR ?= workspace/document-templates/expanded/$(WORKSPACE_TEMPLATE_NAME)
FRESH_TRANSLATION_TREE_DIR ?= outputs/translation-trees/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)/fresh/$(WORKSPACE_TEMPLATE_NAME)
GENERATED_CI_CONFIG ?= config/.generated-regression.ci.yml
GENERATED_CI_CONFIG_DIR ?= config
MERGED_TRANSLATION_TREE_DIR ?= outputs/translation-trees/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)/merged/$(WORKSPACE_TEMPLATE_NAME)
PACKAGE_OUT ?= template.zip
PROJECT_REF ?= fixtures/projects/demo/test-project.json
PROJECT_RENDER_FORMAT_UUID ?= 68c26e34-5e77-4e15-9bf7-06ff92582257
PROJECT_RENDER_OUTPUT ?= outputs/project-render/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)/test-project.pdf
PROJECT_RENDER_TEMPLATE_DIR ?= $(TRANSLATED_EXPANDED_TEMPLATE_DIR)
PROJECT_RENDER_TEMPLATE_PACKAGE ?=
PROJECT_UUID ?= $(DSW_PROJECT_UUID)
PYTHON ?= $(VENV_PYTHON)
PYTHON_LINT_PATHS ?= docs/conf.py scripts/ci/*.py src tests
REBUILT_TEMPLATE_DIR ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/rebuilt/$(WORKSPACE_TEMPLATE_NAME)
REGRESSION_EVIDENCE_CONFIG ?= config/regression-evidence.yml
REGRESSION_EVIDENCE_OUTPUT_DIR ?= outputs/runtime-evidence/$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)
REGRESSION_OUTPUT_DIR ?= outputs/preview
REGRESSION_PLAN_PATH ?= $(COMPAT_LEDGER_DIR)/regression-plan.json
REGRESSION_SUMMARY_LABEL ?= Render Regression Coverage
SCAFFOLD_ARTIFACT_ROOT ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)
SCAFFOLD_TEMPLATE_ID ?= $(TRANSLATED_TEMPLATE_ID)-scaffold
SCAFFOLD_TEMPLATE_NAME ?= $(TRANSLATED_TEMPLATE_NAME) Scaffold
SOURCE_TEMPLATE_ID ?= dsw-science-europe
SOURCE_TEMPLATE_VERSION ?= 1.30.0
SOURCE_TEMPLATE_VERSION_TAG ?= v$(SOURCE_TEMPLATE_VERSION)
SPHINXOPTS ?= -W --keep-going
TEMPLATE_DIR ?=
TOOL_GITHUB_REPO ?= $(if $(GITHUB_REPOSITORY),$(GITHUB_REPOSITORY),$(shell gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null))
TRANSLATED_EXPANDED_TEMPLATE_DIR ?= $(TRANSLATED_OUTPUT_ROOT)/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME)
TRANSLATED_OUTPUT_ROOT ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)
TRANSLATED_REGRESSION_CONFIG ?= config/.generated-regression.translated.yml
TRANSLATED_REGRESSION_METAMODEL_VERSION ?= $(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)
TRANSLATED_REGRESSION_OUTPUT_DIR ?= outputs/translated-regression/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)
TRANSLATED_TEMPLATE_DESCRIPTION ?= Science Europe DMP Template 的繁體中文化版本
TRANSLATED_TEMPLATE_ID ?= science-europe-zh-hant
TRANSLATED_TEMPLATE_NAME ?= Science Europe DMP Template (zh-Hant)
TRANSLATED_TEMPLATE_ORGANIZATION_ID ?= dsw
TRANSLATED_TEMPLATE_PACKAGE ?= $(TRANSLATED_OUTPUT_ROOT)/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME).zip
TRANSLATED_TEMPLATE_VERSION ?= $(SOURCE_TEMPLATE_VERSION)
TRANSLATED_WORKSPACE_TEMPLATE_NAME ?= $(TRANSLATED_TEMPLATE_ORGANIZATION_ID)-$(TRANSLATED_TEMPLATE_ID)-$(TRANSLATED_TEMPLATE_VERSION)
TRANSLATION_CLEAN_ARTIFACT_ROOT ?= $(CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR)
TRANSLATION_CONFIG_PATH ?= $(TRANSLATION_REPO)/translation-config.yml
TRANSLATION_CONSISTENCY_FETCH ?= false
TRANSLATION_CONSISTENCY_JSON_REPORT ?= outputs/translation-consistency/report.json
TRANSLATION_CONSISTENCY_MARKDOWN_REPORT ?= outputs/translation-consistency/report.md
TRANSLATION_CONSISTENCY_VERSIONS ?=
TRANSLATION_DOCS_REPO ?= $(TRANSLATION_REPO)
TRANSLATION_LOCALE ?= zh-Hant
TRANSLATION_MIGRATION_FAIL_ON_PENDING ?= false
TRANSLATION_REPO ?= ../science-europe-template-zh_Hant
TRANSLATION_SOURCE_LOCALE ?= en
TRANSLATION_SYNC_DRY_RUN ?= true
TRANSLATION_SYNC_POLICY_MODE ?= auto
TRANSLATION_SYNC_PUSH ?= false
TRANSLATION_SYNC_REFRESH_EXISTING ?= true
TRANSLATION_SYNC_WORKFLOWS ?= false
TRANSLATION_TARGET_LANG ?= zh_Hant
TRANSLATION_TREE_DIR ?= workspace/document-templates/translation/$(WORKSPACE_TEMPLATE_NAME)
UPSTREAM_TEMPLATE_ARTIFACT_CACHE_ROOT ?= .cache/upstream-artifacts
UPSTREAM_TEMPLATE_ARTIFACT_METAMODEL_VERSION ?=
UPSTREAM_TEMPLATE_ARTIFACT_MIN_REF ?= v1.29.1
UPSTREAM_TEMPLATE_ARTIFACT_REFS ?= $(UPSTREAM_TEMPLATE_ARTIFACT_MIN_REF)+
UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT ?= outputs/upstream-workspaces/$(SOURCE_TEMPLATE_ID)
UPSTREAM_TEMPLATE_CACHE ?= .cache/upstream/science-europe-template
UPSTREAM_TEMPLATE_DISCOVERY_REFS ?= $(UPSTREAM_TEMPLATE_ARTIFACT_REFS)
UPSTREAM_TEMPLATE_DISCOVERY_REPORT ?=
UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION ?= 18.0
UPSTREAM_TEMPLATE_REF ?= latest
UPSTREAM_TEMPLATE_REGRESSION_VERSION ?= latest
UPSTREAM_TEMPLATE_REMOTE ?= $(if $(filter http% git@% ssh://% git://% file://%,$(UPSTREAM_TEMPLATE_REPOSITORY)),$(UPSTREAM_TEMPLATE_REPOSITORY),https://github.com/$(UPSTREAM_TEMPLATE_REPOSITORY).git)
UPSTREAM_TEMPLATE_REPOSITORY ?= https://github.com/ds-wizard/science-europe-template.git
UPSTREAM_TEMPLATE_TEST_METAMODEL_VERSION ?=
UPSTREAM_TEMPLATE_TEST_MIN_REF ?= v1.30.0
UPSTREAM_TEMPLATE_TEST_REFS ?= latest main $(UPSTREAM_TEMPLATE_TEST_MIN_REF)+
UPSTREAM_TEMPLATE_TEST_ROOT ?= .cache/upstream-tag-tests
VENV_DIR ?= .venv
WORKSPACE_TEMPLATE_NAME ?= $(SOURCE_TEMPLATE_ID)-$(SOURCE_TEMPLATE_VERSION)
XLIFF_FILE ?= xliff/$(SOURCE_TEMPLATE_ID).$(TRANSLATION_LOCALE).xlf

VENV_PYTHON := $(VENV_DIR)/bin/python
PIP := $(PYTHON) -m pip

.PHONY: audit-translated-template audit-translation-tree build-upstream-artifacts check check-dsw-runtime-matrix check-translation-migrations check-translation-repository-docs ci-dsw-logs clean compact-template compile create-dsw-compat-pr discover-upstream-compat docs docs-clean download-clean-scaffold-artifacts explain-transform export-fresh-translation-tree export-translation-tree export-xliff fetch-upstream-template format format-check generate-compat-ledger generate-regression-config generate-translated-regression-config help import-xliff install-dev install-hooks lint list-upstream-template-tags merge-translation-tree package-template publish-clean-scaffold-releases render-package render-project render-regression render-regression-ci render-regression-ci-plan render-regression-ci-plan-dry-run render-translated-package-regression render-upstream-artifact-previews report-translation-consistency start-ci-dsw stop-ci-dsw summarize-regression-coverage sync-dsw-runtime-matrix sync-translation-tree sync-translation-version-branches test test-infra test-unit test-upstream-tags transform validate-translation-config venv verify-runtime-evidence verify-template verify-workspace

venv: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(BOOTSTRAP_PYTHON) -m venv $(VENV_DIR)

help:
	@printf '%s\n' \
	'Available targets:' \
	'  audit-translated-template Check translated output kept expanded template structure' \
	'  audit-translation-tree Check translation blocks for unsafe Jinja/control syntax' \
	'  build-upstream-artifacts Build clean multi-version workspaces and scaffold packages' \
	'  check             Run the standard local maintainer checks' \
	'  check-dsw-runtime-matrix Check workflow matrix matches config/dsw-compat.yml' \
	'  check-translation-migrations Dry-run exact-source sync across active translation branches' \
	'  check-translation-repository-docs Check public-repo docs cover required operations topics' \
	'  ci-dsw-logs       Collect local DSW stack logs under outputs/ci-dsw' \
	'  clean             Remove generated outputs and local test/lint caches' \
	'  compact-template  Rebuild $(EXPANDED_TEMPLATE_DIR) into $(REBUILT_TEMPLATE_DIR)' \
	'  compile           Run Python syntax compilation checks' \
	'  create-dsw-compat-pr Create/update a DSW compatibility probe PR from $(COMPAT_PROBE_REPORT)' \
	'  discover-upstream-compat Check upstream template tags have configured DSW runtimes' \
	'  docs              Build the Sphinx documentation site' \
	'  docs-clean        Remove generated Sphinx documentation output' \
	'  download-clean-scaffold-artifacts Download clean scaffold artifacts from a tool workflow run' \
	'  explain-transform Show named profile rewrites recorded in the expanded workspace' \
	'  export-fresh-translation-tree Export $(EXPANDED_TEMPLATE_DIR) into $(FRESH_TRANSLATION_TREE_DIR)' \
	'  export-translation-tree Export $(EXPANDED_TEMPLATE_DIR) into $(TRANSLATION_TREE_DIR)' \
	'  export-xliff Export $(TRANSLATION_TREE_DIR) into $(XLIFF_FILE)' \
	'  fetch-upstream-template Fetch upstream template into $(UPSTREAM_TEMPLATE_CACHE)' \
	'  format            Auto-fix imports/style and format Python files' \
	'  format-check      Check formatting without modifying files' \
	'  generate-compat-ledger Generate offline expanded/tree compatibility fingerprints' \
	'  generate-regression-config Generate CI regression config for the latest built upstream workspace' \
	'  generate-translated-regression-config Generate full regression config for $(TRANSLATED_TEMPLATE_PACKAGE)' \
	'  help              Show this alphabetized target summary' \
	'  import-xliff Import $(XLIFF_FILE) back into $(TRANSLATION_TREE_DIR)' \
	'  install-dev       Install local package and development dependencies' \
	'  install-hooks     Install local git pre-commit hooks' \
	'  lint              Run Ruff lint checks' \
	'  list-upstream-template-tags Show available upstream Science Europe version tags' \
	'  merge-translation-tree Merge $(TRANSLATION_TREE_DIR) into $(MERGED_TRANSLATION_TREE_DIR)' \
	'  package-template  Run dsw-tdk package for TEMPLATE_DIR=/path/to/template' \
	'  publish-clean-scaffold-releases Stage or publish clean scaffold GitHub release assets' \
	'  render-package    Import PROJECT_RENDER_TEMPLATE_PACKAGE, then render $(PROJECT_REF)' \
	'  render-project    Render PROJECT_UUID or $(PROJECT_REF) with $(PROJECT_RENDER_TEMPLATE_DIR)' \
	'  render-regression Run the DSW headless regression workflow using CONFIG=$(CONFIG)' \
	'  render-regression-ci Generate latest-version CI config and run local DSW regression' \
	'  render-regression-ci-plan Run DSW regression for compatibility-plan recommended versions' \
	'  render-regression-ci-plan-dry-run Validate the compatibility regression plan without DSW' \
	'  render-translated-package-regression Fully render $(TRANSLATED_TEMPLATE_PACKAGE) with generated fixtures' \
	'  render-upstream-artifact-previews Render demo PDFs for built scaffold packages' \
	'  report-translation-consistency Compare wording across active public-repo versions' \
	'  start-ci-dsw      Start an ephemeral local DSW stack for CI render regression' \
	'  stop-ci-dsw       Stop the ephemeral local DSW stack and remove volumes' \
	'  summarize-regression-coverage Summarize versioned render and branch coverage reports' \
	'  sync-dsw-runtime-matrix Refresh workflow matrix from config/dsw-compat.yml' \
	'  sync-translation-tree Apply translations and package $(TRANSLATED_TEMPLATE_PACKAGE)' \
	'  sync-translation-version-branches Create/refresh public-repo sync/v* branches' \
	'  test              Run all pytest suites' \
	'  test-infra        Run infrastructure/CLI pytest suites' \
	'  test-unit         Run unit/regression helper pytest suites' \
	'  test-upstream-tags Validate transform/export/sync/package for upstream refs' \
	'  transform         Expand $(COMPACT_TEMPLATE_DIR) into $(EXPANDED_TEMPLATE_DIR)' \
	'  validate-translation-config Validate public-repo translation-config.yml' \
	'  venv              Create $(VENV_DIR) when it does not exist' \
	'  verify-runtime-evidence Require KM, full coverage, regression, and PDF proof' \
	'  verify-template   Run dsw-tdk verify for TEMPLATE_DIR=/path/to/template' \
	'  verify-workspace  Run dsw-tdk verify for generated compact and expanded workspaces'

install-dev: venv
	$(PIP) install -e ".[dev]"

install-hooks: venv
	$(PYTHON) -m pre_commit install

check: format-check lint test

compile: venv
	$(PYTHON) -m compileall -q $(PYTHON_LINT_PATHS)

format: venv
	$(PYTHON) scripts/ci/sync_dsw_runtime_matrix.py
	$(PYTHON) -m ruff check --config config/ruff.toml --fix $(PYTHON_LINT_PATHS)
	$(PYTHON) -m ruff format --config config/ruff.toml $(PYTHON_LINT_PATHS)

format-check: venv
	$(PYTHON) -m ruff format --check --config config/ruff.toml $(PYTHON_LINT_PATHS)
	$(PYTHON) scripts/ci/sync_dsw_runtime_matrix.py --check

lint: venv
	$(PYTHON) -m ruff check --config config/ruff.toml $(PYTHON_LINT_PATHS)

test: test-infra test-unit

test-infra: venv
	$(PYTHON) -m pytest tests/infra

test-unit: venv
	$(PYTHON) -m pytest tests/unit

sync-dsw-runtime-matrix: venv
	$(PYTHON) scripts/ci/sync_dsw_runtime_matrix.py

check-dsw-runtime-matrix: venv
	$(PYTHON) scripts/ci/sync_dsw_runtime_matrix.py --check

check-translation-migrations: venv
	@set -euo pipefail; \
	args=( \
		--repo "$(TRANSLATION_REPO)" \
		--tooling-root "." \
	); \
	if [ "$(TRANSLATION_MIGRATION_FAIL_ON_PENDING)" = "true" ]; then \
		args+=(--fail-on-pending); \
	fi; \
	TRANSLATION_CLEAN_ARTIFACT_ROOT="$(TRANSLATION_CLEAN_ARTIFACT_ROOT)" \
		$(PYTHON) scripts/ci/check_translation_migration_status.py "$${args[@]}"

check-translation-repository-docs: venv
	$(PYTHON) scripts/ci/check_translation_repository_docs.py \
		--repo "$(TRANSLATION_DOCS_REPO)"

report-translation-consistency: venv
	@set -euo pipefail; \
	args=(); \
	if [ "$(TRANSLATION_CONSISTENCY_FETCH)" = "true" ]; then \
		args+=(--fetch); \
	fi; \
	version_args=(); \
	for version in $(TRANSLATION_CONSISTENCY_VERSIONS); do \
		version_args+=(--version "$$version"); \
	done; \
	$(PYTHON) scripts/ci/report_translation_consistency.py \
		--repo "$(TRANSLATION_REPO)" \
		--json-report "$(TRANSLATION_CONSISTENCY_JSON_REPORT)" \
		--markdown-report "$(TRANSLATION_CONSISTENCY_MARKDOWN_REPORT)" \
		"$${args[@]}" \
		"$${version_args[@]}"

create-dsw-compat-pr: venv
	@set -euo pipefail; \
	args=( \
		--report "$(COMPAT_PROBE_REPORT)" \
		--compat "$(DSW_COMPAT_CONFIG)" \
		--evidence-config "$(REGRESSION_EVIDENCE_CONFIG)" \
		--report-path "$(COMPAT_PROBE_REPORT_PATH)" \
		--repository "$(TOOL_GITHUB_REPO)" \
		--base "$(COMPAT_PROBE_BASE_BRANCH)" \
	); \
	if [ "$(COMPAT_PROBE_DRY_RUN)" = "true" ]; then \
		args+=(--dry-run); \
	fi; \
	$(PYTHON) scripts/ci/create_dsw_compat_pr.py "$${args[@]}"

verify-template: venv
	@test -n "$(TEMPLATE_DIR)" || (echo "Set TEMPLATE_DIR=/path/to/template" && exit 2)
	$(DSW_TDK) verify $(TEMPLATE_DIR)

verify-workspace: transform venv
	$(DSW_TDK) verify $(COMPACT_TEMPLATE_DIR)
	$(DSW_TDK) verify $(EXPANDED_TEMPLATE_DIR)

package-template: venv
	@test -n "$(TEMPLATE_DIR)" || (echo "Set TEMPLATE_DIR=/path/to/template" && exit 2)
	$(DSW_TDK) package $(TEMPLATE_DIR) --output $(PACKAGE_OUT) --force

transform: venv
	$(DSW_TEMPLATE_TRANSFORM) expand --source $(COMPACT_TEMPLATE_DIR) --output $(EXPANDED_TEMPLATE_DIR)

explain-transform: transform venv
	$(DSW_TEMPLATE_TRANSFORM) explain --source $(EXPANDED_TEMPLATE_DIR)

export-translation-tree: transform venv
	$(DSW_TEMPLATE_TREE) export --source $(EXPANDED_TEMPLATE_DIR) --output $(TRANSLATION_TREE_DIR)

export-fresh-translation-tree: transform venv
	$(DSW_TEMPLATE_TREE) export --source $(EXPANDED_TEMPLATE_DIR) --output $(FRESH_TRANSLATION_TREE_DIR)

merge-translation-tree: export-fresh-translation-tree venv
	$(DSW_TEMPLATE_TREE) merge \
		--old-tree "$(TRANSLATION_TREE_DIR)" \
		--new-tree "$(FRESH_TRANSLATION_TREE_DIR)" \
		--output "$(MERGED_TRANSLATION_TREE_DIR)" \
		--source-lang "$(TRANSLATION_SOURCE_LOCALE)" \
		--target-lang "$(TRANSLATION_TARGET_LANG)"

export-xliff: venv
	$(DSW_TEMPLATE_TREE) export-xliff \
		--tree "$(TRANSLATION_TREE_DIR)" \
		--output "$(XLIFF_FILE)" \
		--source-lang "$(TRANSLATION_SOURCE_LOCALE)" \
		--target-lang "$(TRANSLATION_TARGET_LANG)"

import-xliff: venv
	$(DSW_TEMPLATE_TREE) import-xliff \
		--tree "$(TRANSLATION_TREE_DIR)" \
		--xliff "$(XLIFF_FILE)" \
		--source-lang "$(TRANSLATION_SOURCE_LOCALE)" \
		--target-lang "$(TRANSLATION_TARGET_LANG)"

audit-translation-tree: venv
	$(DSW_TEMPLATE_TREE) audit --source $(EXPANDED_TEMPLATE_DIR) --tree $(TRANSLATION_TREE_DIR)

sync-translation-tree: audit-translation-tree
	$(DSW_TEMPLATE_TREE) sync \
		--tree "$(TRANSLATION_TREE_DIR)" \
		--source "$(EXPANDED_TEMPLATE_DIR)" \
		--output "$(TRANSLATED_EXPANDED_TEMPLATE_DIR)" \
		--template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
		--template-id "$(TRANSLATED_TEMPLATE_ID)" \
		--template-name "$(TRANSLATED_TEMPLATE_NAME)" \
		--template-description "$(TRANSLATED_TEMPLATE_DESCRIPTION)" \
		--template-version "$(TRANSLATED_TEMPLATE_VERSION)"
	$(DSW_TEMPLATE_TREE) audit-output \
		--source "$(EXPANDED_TEMPLATE_DIR)" \
		--output "$(TRANSLATED_EXPANDED_TEMPLATE_DIR)"
	$(DSW_TDK) package $(TRANSLATED_EXPANDED_TEMPLATE_DIR) --output $(TRANSLATED_TEMPLATE_PACKAGE) --force

audit-translated-template: venv
	$(DSW_TEMPLATE_TREE) audit-output \
		--source "$(EXPANDED_TEMPLATE_DIR)" \
		--output "$(TRANSLATED_EXPANDED_TEMPLATE_DIR)"

compact-template: venv
	$(DSW_TEMPLATE_TRANSFORM) compact --source $(EXPANDED_TEMPLATE_DIR) --output $(REBUILT_TEMPLATE_DIR)

list-upstream-template-tags: venv
	$(PYTHON) scripts/ci/upstream_template_artifacts.py list-tags \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)"

fetch-upstream-template: venv
	$(PYTHON) scripts/ci/upstream_template_artifacts.py fetch \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)" \
		--ref "$(UPSTREAM_TEMPLATE_REF)" \
		--cache "$(UPSTREAM_TEMPLATE_CACHE)"

test-upstream-tags: venv
	$(PYTHON) scripts/ci/upstream_template_artifacts.py test-tags \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)" \
		--refs $(UPSTREAM_TEMPLATE_TEST_REFS) \
		--root "$(UPSTREAM_TEMPLATE_TEST_ROOT)" \
		--test-metamodel-version "$(UPSTREAM_TEMPLATE_TEST_METAMODEL_VERSION)" \
		--tdk-executable "$(DSW_TDK)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--translated-template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
		--translated-template-id "$(TRANSLATED_TEMPLATE_ID)" \
		--translated-template-name "$(TRANSLATED_TEMPLATE_NAME)"

discover-upstream-compat: venv
	UPSTREAM_TEMPLATE_DISCOVERY_REPORT="$(UPSTREAM_TEMPLATE_DISCOVERY_REPORT)" \
		$(PYTHON) scripts/ci/discover_dsw_compat.py \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)" \
		--compat "$(DSW_COMPAT_CONFIG)" \
		--cache ".cache/upstream-compat-discovery" \
		$(UPSTREAM_TEMPLATE_DISCOVERY_REFS)

download-clean-scaffold-artifacts: venv
	@test -n "$(TOOL_GITHUB_REPO)" || { \
		echo "TOOL_GITHUB_REPO is required outside a GitHub checkout" >&2; \
		exit 2; \
	}
	@set -euo pipefail; \
	args=( \
		--repo "$(TOOL_GITHUB_REPO)" \
		--output-dir "$(CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR)" \
	); \
	if [ -n "$(CLEAN_SCAFFOLD_ARTIFACT_RUN_ID)" ]; then \
		args+=(--run-id "$(CLEAN_SCAFFOLD_ARTIFACT_RUN_ID)"); \
	else \
		args+=( \
			--workflow "$(CLEAN_SCAFFOLD_ARTIFACT_WORKFLOW)" \
			--branch "$(CLEAN_SCAFFOLD_ARTIFACT_BRANCH)" \
		); \
	fi; \
	$(PYTHON) scripts/ci/download_clean_scaffold_artifacts.py "$${args[@]}"

docs: venv
	$(PYTHON) -m sphinx -b html $(SPHINXOPTS) "$(DOCS_SOURCE_DIR)" "$(DOCS_BUILD_DIR)"

docs-clean:
	rm -rf docs/_build

build-upstream-artifacts: venv
	$(PYTHON) scripts/ci/upstream_template_artifacts.py build-artifacts \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)" \
		--refs $(UPSTREAM_TEMPLATE_ARTIFACT_REFS) \
		--artifact-cache-root "$(UPSTREAM_TEMPLATE_ARTIFACT_CACHE_ROOT)" \
		--artifact-metamodel-version "$(UPSTREAM_TEMPLATE_ARTIFACT_METAMODEL_VERSION)" \
		--artifact-workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)" \
		--tdk-executable "$(DSW_TDK)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--translation-locale "$(TRANSLATION_LOCALE)" \
		--translated-template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
		--translated-template-id "$(TRANSLATED_TEMPLATE_ID)" \
		--translated-template-name "$(TRANSLATED_TEMPLATE_NAME)" \
		--scaffold-template-id "$(SCAFFOLD_TEMPLATE_ID)" \
		--scaffold-template-name "$(SCAFFOLD_TEMPLATE_NAME)"

generate-compat-ledger: venv
	$(PYTHON) scripts/ci/generate_compat_ledger.py \
		--workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)" \
		--output-dir "$(COMPAT_LEDGER_DIR)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--scaffold-root "$(SCAFFOLD_ARTIFACT_ROOT)" \
		--source-lang "$(TRANSLATION_SOURCE_LOCALE)" \
		--target-lang "$(TRANSLATION_TARGET_LANG)"

generate-regression-config: venv
	$(PYTHON) scripts/ci/generate_regression_config.py \
		--base-config "$(CI_CONFIG)" \
		--compat-config "$(DSW_COMPAT_CONFIG)" \
		--evidence-config "$(REGRESSION_EVIDENCE_CONFIG)" \
		--output "$(GENERATED_CI_CONFIG)" \
		--workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
		--version "$(UPSTREAM_TEMPLATE_REGRESSION_VERSION)"

generate-translated-regression-config: venv
	@test -n "$(TRANSLATED_TEMPLATE_PACKAGE)" || { \
		echo "TRANSLATED_TEMPLATE_PACKAGE is required" >&2; \
		exit 2; \
	}
	$(PYTHON) scripts/ci/generate_translated_regression_config.py \
		--base-config "$(CI_CONFIG)" \
		--compat-config "$(DSW_COMPAT_CONFIG)" \
		--evidence-config "$(REGRESSION_EVIDENCE_CONFIG)" \
		--metamodel-version "$(TRANSLATED_REGRESSION_METAMODEL_VERSION)" \
		--output "$(TRANSLATED_REGRESSION_CONFIG)" \
		--output-dir "$(TRANSLATED_REGRESSION_OUTPUT_DIR)" \
		--package "$(TRANSLATED_TEMPLATE_PACKAGE)"

render-upstream-artifact-previews: venv
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(PYTHON) scripts/ci/upstream_template_artifacts.py render-previews \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--translation-locale "$(TRANSLATION_LOCALE)" \
		--translated-template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
		--scaffold-template-id "$(SCAFFOLD_TEMPLATE_ID)" \
		--project-ref "$(PROJECT_REF)" \
		--format-uuid "$(PROJECT_RENDER_FORMAT_UUID)" \
		--tdk-executable "$(DSW_TDK)" \
		--preview-metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)"

publish-clean-scaffold-releases: venv
	@test -n "$(TOOL_GITHUB_REPO)" || { \
		echo "TOOL_GITHUB_REPO is required outside a GitHub checkout" >&2; \
		exit 2; \
	}
	@set -euo pipefail; \
	args=( \
		--repository "$(TOOL_GITHUB_REPO)" \
		--commit-sha "$(CLEAN_SCAFFOLD_RELEASE_COMMIT_SHA)" \
		--release-root "$(CLEAN_SCAFFOLD_RELEASE_ROOT)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--translation-locale "$(TRANSLATION_LOCALE)" \
	); \
	if [ "$(CLEAN_SCAFFOLD_RELEASE_DRY_RUN)" = "true" ]; then \
		args+=(--dry-run); \
	fi; \
	$(PYTHON) scripts/ci/publish_clean_scaffold_releases.py "$${args[@]}"

start-ci-dsw:
	scripts/ci/start_dsw.sh

stop-ci-dsw:
	scripts/ci/stop_dsw.sh

ci-dsw-logs:
	scripts/ci/collect_dsw_logs.sh

render-package: venv
	@test -n "$(PROJECT_RENDER_TEMPLATE_PACKAGE)" || { \
		echo "PROJECT_RENDER_TEMPLATE_PACKAGE is required for render-package" >&2; \
		exit 2; \
	}
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(DSW_TEMPLATE_RENDER_PROJECT) \
		--project-uuid "$(PROJECT_UUID)" \
		--project-ref "$(PROJECT_REF)" \
		--template-package "$(PROJECT_RENDER_TEMPLATE_PACKAGE)" \
		--format-uuid "$(PROJECT_RENDER_FORMAT_UUID)" \
		--output "$(PROJECT_RENDER_OUTPUT)"

render-project: venv
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(DSW_TEMPLATE_RENDER_PROJECT) \
		--project-uuid "$(PROJECT_UUID)" \
		--project-ref "$(PROJECT_REF)" \
		--template-dir "$(PROJECT_RENDER_TEMPLATE_DIR)" \
		--format-uuid "$(PROJECT_RENDER_FORMAT_UUID)" \
		--output "$(PROJECT_RENDER_OUTPUT)"

render-regression: venv
	$(DSW_TEMPLATE_RENDER_REGRESSION) --config $(CONFIG)

render-regression-ci: generate-regression-config
	DSW_API_URL=$${DSW_API_URL:-http://localhost:$${DSW_CI_API_PORT:-3000}/wizard-api} \
	DSW_EMAIL=$${DSW_EMAIL:-albert.einstein@example.com} \
	DSW_PASSWORD=$${DSW_PASSWORD:-password} \
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(DSW_TEMPLATE_RENDER_REGRESSION) --config "$(GENERATED_CI_CONFIG)"

render-regression-ci-plan: venv
	$(PYTHON) scripts/ci/run_regression_plan.py \
		--base-config "$(CI_CONFIG)" \
		--compat-config "$(DSW_COMPAT_CONFIG)" \
		--evidence-config "$(REGRESSION_EVIDENCE_CONFIG)" \
		--generated-config-dir "$(GENERATED_CI_CONFIG_DIR)" \
		--metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
		--plan "$(REGRESSION_PLAN_PATH)" \
		--render-command "$(DSW_TEMPLATE_RENDER_REGRESSION)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)"

render-regression-ci-plan-dry-run: venv
	$(PYTHON) scripts/ci/run_regression_plan.py \
		--base-config "$(CI_CONFIG)" \
		--compat-config "$(DSW_COMPAT_CONFIG)" \
		--dry-run \
		--evidence-config "$(REGRESSION_EVIDENCE_CONFIG)" \
		--generated-config-dir "$(GENERATED_CI_CONFIG_DIR)" \
		--metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
		--plan "$(REGRESSION_PLAN_PATH)" \
		--render-command "$(DSW_TEMPLATE_RENDER_REGRESSION)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)"

render-translated-package-regression: generate-translated-regression-config
	DSW_API_URL=$${DSW_API_URL:-http://localhost:$${DSW_CI_API_PORT:-3000}/wizard-api} \
	DSW_EMAIL=$${DSW_EMAIL:-albert.einstein@example.com} \
	DSW_PASSWORD=$${DSW_PASSWORD:-password} \
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(DSW_TEMPLATE_RENDER_REGRESSION) --config "$(TRANSLATED_REGRESSION_CONFIG)"

summarize-regression-coverage: venv
	$(PYTHON) scripts/ci/summarize_regression_coverage.py \
		--output-dir "$(REGRESSION_OUTPUT_DIR)" \
		--title "$(REGRESSION_SUMMARY_LABEL)"

verify-runtime-evidence: venv
	$(PYTHON) scripts/ci/verify_runtime_evidence.py \
		--compat-config "$(DSW_COMPAT_CONFIG)" \
		--evidence-config "$(REGRESSION_EVIDENCE_CONFIG)" \
		--metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
		--output-dir "$(REGRESSION_EVIDENCE_OUTPUT_DIR)" \
		--plan "$(REGRESSION_PLAN_PATH)" \
		--preview-root "outputs/project-render" \
		--regression-root "$(REGRESSION_OUTPUT_DIR)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--translation-locale "$(TRANSLATION_LOCALE)"

sync-translation-version-branches: venv
	@set -euo pipefail; \
	args=( \
		--repo "$(TRANSLATION_REPO)" \
		--tooling-root "." \
		--clean-artifact-root "$(TRANSLATION_CLEAN_ARTIFACT_ROOT)" \
		--tdk-executable "$(DSW_TDK)" \
		--policy-mode "$(TRANSLATION_SYNC_POLICY_MODE)" \
	); \
	if [ "$(TRANSLATION_SYNC_DRY_RUN)" = "true" ]; then \
		args+=(--dry-run); \
	fi; \
	if [ "$(TRANSLATION_SYNC_PUSH)" = "true" ]; then \
		args+=(--push); \
	fi; \
	if [ "$(TRANSLATION_SYNC_REFRESH_EXISTING)" = "true" ]; then \
		args+=(--refresh-existing); \
	fi; \
	if [ "$(TRANSLATION_SYNC_WORKFLOWS)" = "true" ]; then \
		args+=(--sync-workflows); \
	fi; \
	$(PYTHON) scripts/ci/sync_translation_version_branches.py "$${args[@]}"

validate-translation-config: venv
	$(PYTHON) scripts/ci/validate_translation_config.py \
		--config "$(TRANSLATION_CONFIG_PATH)"

clean:
	rm -rf outputs dist build docs/_build .pytest_cache .ruff_cache
	rm -f config/.generated-*.yml
	find . -path './.venv' -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' ! -path './.venv/*' -delete
