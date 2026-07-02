SHELL := bash

# Keep user-overridable defaults in lexicographic order; tests enforce this so
# CI/maintenance knobs stay easy to scan.
BOOTSTRAP_PYTHON ?= python3
CI_CONFIG ?= config/regression.ci.yml
COMPACT_TEMPLATE_DIR ?= workspace/document-templates/compact/$(WORKSPACE_TEMPLATE_NAME)
COMPAT_LEDGER_DIR ?= outputs/compat-ledger/$(SOURCE_TEMPLATE_ID)
CONFIG ?= config/regression.preview.yml
DSW_COMPAT_CONFIG ?= config/dsw-compat.yml
DSW_TDK ?= $(VENV_DIR)/bin/dsw-tdk
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
PROJECT_UUID ?= $(DSW_PROJECT_UUID)
PUBLISH_BASE_BRANCH ?= main
PUBLISH_VERSION ?= $(SOURCE_TEMPLATE_VERSION_TAG)
PYTHON ?= $(VENV_PYTHON)
PYTHON_LINT_PATHS ?= src tests scripts/ci/*.py
REBUILT_TEMPLATE_DIR ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/rebuilt/$(WORKSPACE_TEMPLATE_NAME)
REGRESSION_PLAN_PATH ?= $(COMPAT_LEDGER_DIR)/regression-plan.json
REGRESSION_SMOKE_GENERATED_FIXTURE_COUNT ?= 20
SCAFFOLD_ARTIFACT_ROOT ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)
SCAFFOLD_TEMPLATE_ID ?= $(TRANSLATED_TEMPLATE_ID)-scaffold
SCAFFOLD_TEMPLATE_NAME ?= $(TRANSLATED_TEMPLATE_NAME) Scaffold
SOURCE_TEMPLATE_ID ?= dsw-science-europe
SOURCE_TEMPLATE_VERSION ?= 1.30.0
SOURCE_TEMPLATE_VERSION_TAG ?= v$(SOURCE_TEMPLATE_VERSION)
TEMPLATE_DIR ?=
TRANSLATED_EXPANDED_TEMPLATE_DIR ?= $(TRANSLATED_OUTPUT_ROOT)/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME)
TRANSLATED_OUTPUT_ROOT ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)
TRANSLATED_TEMPLATE_ID ?= science-europe-zh-hant
TRANSLATED_TEMPLATE_NAME ?= Science Europe DMP Template (zh-Hant)
TRANSLATED_TEMPLATE_ORGANIZATION_ID ?= dsw
TRANSLATED_TEMPLATE_PACKAGE ?= $(TRANSLATED_OUTPUT_ROOT)/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME).zip
TRANSLATED_TEMPLATE_VERSION ?= $(SOURCE_TEMPLATE_VERSION)
TRANSLATED_WORKSPACE_TEMPLATE_NAME ?= $(TRANSLATED_TEMPLATE_ORGANIZATION_ID)-$(TRANSLATED_TEMPLATE_ID)-$(TRANSLATED_TEMPLATE_VERSION)
TRANSLATION_LOCALE ?= zh-Hant
TRANSLATION_REPO ?= ../DSW-document-template-translation
TRANSLATION_SOURCE_LOCALE ?= en
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
UPSTREAM_TEMPLATE_PREVIEW_STRICT ?= true
UPSTREAM_TEMPLATE_REF ?= latest
UPSTREAM_TEMPLATE_REGRESSION_VERSION ?= latest
UPSTREAM_TEMPLATE_REMOTE ?= $(if $(filter http% git@% ssh://% git://% file://%,$(UPSTREAM_TEMPLATE_REPOSITORY)),$(UPSTREAM_TEMPLATE_REPOSITORY),https://github.com/$(UPSTREAM_TEMPLATE_REPOSITORY).git)
UPSTREAM_TEMPLATE_REPOSITORY ?= https://github.com/ds-wizard/science-europe-template.git
UPSTREAM_TEMPLATE_TEST_METAMODEL_VERSION ?=
UPSTREAM_TEMPLATE_TEST_MIN_REF ?= v1.30.0
UPSTREAM_TEMPLATE_TEST_REFS ?= latest main $(UPSTREAM_TEMPLATE_TEST_MIN_REF)+
UPSTREAM_TEMPLATE_TEST_ROOT ?= .cache/upstream-tag-tests
VENV_DIR ?= .venv
WEBLATE_XLIFF ?= weblate/$(SOURCE_TEMPLATE_ID).$(TRANSLATION_LOCALE).xlf
WORKSPACE_TEMPLATE_NAME ?= $(SOURCE_TEMPLATE_ID)-$(SOURCE_TEMPLATE_VERSION)

VENV_PYTHON := $(VENV_DIR)/bin/python
PIP := $(PYTHON) -m pip

.PHONY: audit-translated-template audit-translation-tree build-upstream-artifacts check-dsw-runtime-matrix ci-dsw-logs clean compact-template compile discover-upstream-compat export-fresh-translation-tree export-translation-tree export-weblate-xliff fetch-upstream-template format format-check generate-compat-ledger generate-regression-config help import-weblate-xliff install-dev install-hooks lint list-upstream-template-tags merge-translation-tree package-template publish-translated-template render-project render-regression render-regression-ci render-regression-ci-plan render-upstream-artifact-previews start-ci-dsw stop-ci-dsw sync-dsw-runtime-matrix sync-translation-tree test test-infra test-unit test-upstream-tags transform venv verify-template verify-workspace

venv: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(BOOTSTRAP_PYTHON) -m venv $(VENV_DIR)

help:
	@printf '%s\n' \
	'Available targets:' \
	'  venv              Create $(VENV_DIR) when it does not exist' \
	'  install-dev       Install local dev dependencies from config/requirements.txt' \
	'  install-hooks     Install local git pre-commit hooks' \
	'  compile           Run Python syntax compilation checks' \
	'  format            Auto-fix imports/style and format Python files' \
	'  format-check      Check formatting without modifying files' \
	'  lint              Run Ruff lint checks' \
	'  test              Run all pytest suites' \
	'  test-infra        Run infrastructure/CLI pytest suites' \
	'  test-unit         Run unit/regression helper pytest suites' \
	'  sync-dsw-runtime-matrix Refresh workflow matrix from config/dsw-compat.yml' \
	'  check-dsw-runtime-matrix Check workflow matrix matches config/dsw-compat.yml' \
	'  clean             Remove generated outputs and local test/lint caches' \
	'  verify-template   Run dsw-tdk verify for TEMPLATE_DIR=/path/to/template' \
	'  verify-workspace  Run dsw-tdk verify for generated compact and expanded workspaces' \
	'  package-template  Run dsw-tdk package for TEMPLATE_DIR=/path/to/template' \
	'  transform         Expand $(COMPACT_TEMPLATE_DIR) into $(EXPANDED_TEMPLATE_DIR)' \
	'  export-translation-tree Export $(EXPANDED_TEMPLATE_DIR) into $(TRANSLATION_TREE_DIR)' \
	'  export-fresh-translation-tree Export $(EXPANDED_TEMPLATE_DIR) into $(FRESH_TRANSLATION_TREE_DIR)' \
	'  merge-translation-tree Merge $(TRANSLATION_TREE_DIR) into $(MERGED_TRANSLATION_TREE_DIR)' \
	'  export-weblate-xliff Export $(TRANSLATION_TREE_DIR) into $(WEBLATE_XLIFF)' \
	'  import-weblate-xliff Import $(WEBLATE_XLIFF) back into $(TRANSLATION_TREE_DIR)' \
	'  audit-translation-tree Check translation blocks for unsafe Jinja/control syntax' \
	'  sync-translation-tree Apply translations and package $(TRANSLATED_TEMPLATE_PACKAGE)' \
	'  audit-translated-template Check translated output kept expanded template structure' \
	'  compact-template  Rebuild $(EXPANDED_TEMPLATE_DIR) into $(REBUILT_TEMPLATE_DIR)' \
	'  list-upstream-template-tags Show available upstream Science Europe version tags' \
	'  fetch-upstream-template Fetch upstream template into $(UPSTREAM_TEMPLATE_CACHE)' \
	'  test-upstream-tags Smoke-test transform/export/sync/package for upstream refs' \
	'  discover-upstream-compat Check upstream template tags have configured DSW runtimes' \
	'  build-upstream-artifacts Build clean multi-version workspaces and scaffold packages' \
	'  generate-compat-ledger Generate offline expanded/tree compatibility fingerprints' \
	'  generate-regression-config Generate CI regression config for the latest built upstream workspace' \
	'  render-upstream-artifact-previews Render demo PDFs for built scaffold packages' \
	'  publish-translated-template Manually publish a translated version branch to its target repository' \
	'  start-ci-dsw      Start an ephemeral local DSW stack for CI render regression' \
	'  stop-ci-dsw       Stop the ephemeral local DSW stack and remove volumes' \
	'  ci-dsw-logs       Collect local DSW stack logs under outputs/ci-dsw' \
	'  render-project    Render PROJECT_UUID or $(PROJECT_REF) with $(PROJECT_RENDER_TEMPLATE_DIR)' \
	'  render-regression Run the DSW headless regression workflow using CONFIG=$(CONFIG)' \
	'  render-regression-ci Generate latest-version CI config and run local DSW regression' \
	'  render-regression-ci-plan Run DSW regression for compatibility-plan recommended versions'

install-dev: venv
	$(PIP) install -r config/requirements.txt

install-hooks: venv
	$(PYTHON) -m pre_commit install

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
	$(PYTHON) src/transform_template.py expand --source $(COMPACT_TEMPLATE_DIR) --output $(EXPANDED_TEMPLATE_DIR)

export-translation-tree: transform venv
	$(PYTHON) src/translation_tree.py export --source $(EXPANDED_TEMPLATE_DIR) --output $(TRANSLATION_TREE_DIR)

export-fresh-translation-tree: transform venv
	$(PYTHON) src/translation_tree.py export --source $(EXPANDED_TEMPLATE_DIR) --output $(FRESH_TRANSLATION_TREE_DIR)

merge-translation-tree: export-fresh-translation-tree venv
	$(PYTHON) src/translation_tree.py merge \
		--old-tree "$(TRANSLATION_TREE_DIR)" \
		--new-tree "$(FRESH_TRANSLATION_TREE_DIR)" \
		--output "$(MERGED_TRANSLATION_TREE_DIR)" \
		--source-lang "$(TRANSLATION_SOURCE_LOCALE)" \
		--target-lang "$(TRANSLATION_TARGET_LANG)"

export-weblate-xliff: venv
	$(PYTHON) src/translation_tree.py export-xliff \
		--tree "$(TRANSLATION_TREE_DIR)" \
		--output "$(WEBLATE_XLIFF)" \
		--source-lang "$(TRANSLATION_SOURCE_LOCALE)" \
		--target-lang "$(TRANSLATION_TARGET_LANG)"

import-weblate-xliff: venv
	$(PYTHON) src/translation_tree.py import-xliff \
		--tree "$(TRANSLATION_TREE_DIR)" \
		--xliff "$(WEBLATE_XLIFF)" \
		--source-lang "$(TRANSLATION_SOURCE_LOCALE)" \
		--target-lang "$(TRANSLATION_TARGET_LANG)"

audit-translation-tree: venv
	$(PYTHON) src/translation_tree.py audit --source $(EXPANDED_TEMPLATE_DIR) --tree $(TRANSLATION_TREE_DIR)

sync-translation-tree: audit-translation-tree
	$(PYTHON) src/translation_tree.py sync \
		--tree "$(TRANSLATION_TREE_DIR)" \
		--source "$(EXPANDED_TEMPLATE_DIR)" \
		--output "$(TRANSLATED_EXPANDED_TEMPLATE_DIR)" \
		--template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
		--template-id "$(TRANSLATED_TEMPLATE_ID)" \
		--template-name "$(TRANSLATED_TEMPLATE_NAME)" \
		--template-version "$(TRANSLATED_TEMPLATE_VERSION)"
	$(PYTHON) src/translation_tree.py audit-output \
		--source "$(EXPANDED_TEMPLATE_DIR)" \
		--output "$(TRANSLATED_EXPANDED_TEMPLATE_DIR)"
	$(DSW_TDK) package $(TRANSLATED_EXPANDED_TEMPLATE_DIR) --output $(TRANSLATED_TEMPLATE_PACKAGE) --force

audit-translated-template: venv
	$(PYTHON) src/translation_tree.py audit-output \
		--source "$(EXPANDED_TEMPLATE_DIR)" \
		--output "$(TRANSLATED_EXPANDED_TEMPLATE_DIR)"

compact-template: venv
	$(PYTHON) src/transform_template.py compact --source $(EXPANDED_TEMPLATE_DIR) --output $(REBUILT_TEMPLATE_DIR)

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
		--python "$(PYTHON)" \
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

build-upstream-artifacts: venv
	$(PYTHON) scripts/ci/upstream_template_artifacts.py build-artifacts \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)" \
		--refs $(UPSTREAM_TEMPLATE_ARTIFACT_REFS) \
		--artifact-cache-root "$(UPSTREAM_TEMPLATE_ARTIFACT_CACHE_ROOT)" \
		--artifact-metamodel-version "$(UPSTREAM_TEMPLATE_ARTIFACT_METAMODEL_VERSION)" \
		--artifact-workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)" \
		--python "$(PYTHON)" \
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
		--output "$(GENERATED_CI_CONFIG)" \
		--workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
		--version "$(UPSTREAM_TEMPLATE_REGRESSION_VERSION)"

render-upstream-artifact-previews: venv
	$(PYTHON) scripts/ci/upstream_template_artifacts.py render-previews \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--translation-locale "$(TRANSLATION_LOCALE)" \
		--translated-template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
		--scaffold-template-id "$(SCAFFOLD_TEMPLATE_ID)" \
		--project-ref "$(PROJECT_REF)" \
		--format-uuid "$(PROJECT_RENDER_FORMAT_UUID)" \
		--tdk-executable "$(DSW_TDK)" \
		--preview-metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
		--preview-strict "$(UPSTREAM_TEMPLATE_PREVIEW_STRICT)" \
		--python "$(PYTHON)"

publish-translated-template: venv
	$(PYTHON) scripts/ci/publish_translated_template.py \
		--translation-repo "$(TRANSLATION_REPO)" \
		--version "$(PUBLISH_VERSION)" \
		--base-branch "$(PUBLISH_BASE_BRANCH)" \
		--push

start-ci-dsw:
	scripts/ci/start_dsw.sh

stop-ci-dsw:
	scripts/ci/stop_dsw.sh

ci-dsw-logs:
	scripts/ci/collect_dsw_logs.sh

render-project: venv
	$(PYTHON) src/render_project.py \
		--project-uuid "$(PROJECT_UUID)" \
		--project-ref "$(PROJECT_REF)" \
		--template-dir "$(PROJECT_RENDER_TEMPLATE_DIR)" \
		--format-uuid "$(PROJECT_RENDER_FORMAT_UUID)" \
		--output "$(PROJECT_RENDER_OUTPUT)"

render-regression: venv
	$(PYTHON) src/render_regression.py --config $(CONFIG)

render-regression-ci: generate-regression-config
	DSW_API_URL=$${DSW_API_URL:-http://localhost:$${DSW_CI_API_PORT:-3000}/wizard-api} \
	DSW_EMAIL=$${DSW_EMAIL:-albert.einstein@example.com} \
	DSW_PASSWORD=$${DSW_PASSWORD:-password} \
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(PYTHON) src/render_regression.py --config "$(GENERATED_CI_CONFIG)"

render-regression-ci-plan: venv
	$(PYTHON) scripts/ci/run_regression_plan.py \
		--base-config "$(CI_CONFIG)" \
		--fallback-version "$(UPSTREAM_TEMPLATE_REGRESSION_VERSION)" \
		--generated-config-dir "$(GENERATED_CI_CONFIG_DIR)" \
		--metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
		--plan "$(REGRESSION_PLAN_PATH)" \
		--python "$(PYTHON)" \
		--render-script "src/render_regression.py" \
		--smoke-generated-fixture-count "$(REGRESSION_SMOKE_GENERATED_FIXTURE_COUNT)" \
		--source-template-id "$(SOURCE_TEMPLATE_ID)" \
		--workspace-root "$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)"

clean:
	rm -rf outputs dist build .pytest_cache .ruff_cache
	find . -path './.venv' -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' ! -path './.venv/*' -delete
