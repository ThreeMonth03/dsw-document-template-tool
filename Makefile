VENV_DIR ?= .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
BOOTSTRAP_PYTHON ?= python3
PYTHON ?= $(VENV_PYTHON)
PIP := $(PYTHON) -m pip
DSW_TDK ?= $(VENV_DIR)/bin/dsw-tdk

CONFIG ?= config/regression.preview.yml
CI_CONFIG ?= config/regression.ci.yml
TEMPLATE_DIR ?=
PACKAGE_OUT ?= template.zip
WORKSPACE_TEMPLATE_NAME ?= dsw-science-europe-1.30.0
TRANSLATED_TEMPLATE_ORGANIZATION_ID ?= dsw
TRANSLATED_TEMPLATE_ID ?= science-europe-zh-hant
TRANSLATED_TEMPLATE_VERSION ?= 1.30.0
TRANSLATED_TEMPLATE_NAME ?= Science Europe DMP Template (zh-Hant)
TRANSLATED_WORKSPACE_TEMPLATE_NAME ?= $(TRANSLATED_TEMPLATE_ORGANIZATION_ID)-$(TRANSLATED_TEMPLATE_ID)-$(TRANSLATED_TEMPLATE_VERSION)
COMPACT_TEMPLATE_DIR ?= workspace/document-templates/compact/$(WORKSPACE_TEMPLATE_NAME)
EXPANDED_TEMPLATE_DIR ?= workspace/document-templates/expanded/$(WORKSPACE_TEMPLATE_NAME)
TRANSLATION_TREE_DIR ?= workspace/document-templates/translation/$(WORKSPACE_TEMPLATE_NAME)
REBUILT_TEMPLATE_DIR ?= outputs/document-templates/rebuilt/$(WORKSPACE_TEMPLATE_NAME)
TRANSLATED_EXPANDED_TEMPLATE_DIR ?= outputs/document-templates/translated-expanded/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME)
TRANSLATED_TEMPLATE_PACKAGE ?= outputs/document-templates/translated-expanded/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME).zip
PROJECT_REF ?= workspace/projects/test-project.json
PROJECT_UUID ?= $(DSW_PROJECT_UUID)
PROJECT_RENDER_TEMPLATE_DIR ?= $(TRANSLATED_EXPANDED_TEMPLATE_DIR)
PROJECT_RENDER_FORMAT_UUID ?= 68c26e34-5e77-4e15-9bf7-06ff92582257
PROJECT_RENDER_OUTPUT ?= outputs/project-render/test-project.pdf

.PHONY: help venv install-dev install-hooks compile format format-check lint test test-infra test-unit verify-template verify-workspace package-template transform compact-template export-translation-tree audit-translation-tree sync-translation-tree audit-translated-template start-ci-dsw stop-ci-dsw ci-dsw-logs render-project render-regression render-regression-ci clean

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
	'  clean             Remove generated outputs and local test/lint caches' \
	'  verify-template   Run dsw-tdk verify for TEMPLATE_DIR=/path/to/template' \
	'  verify-workspace  Run dsw-tdk verify for checked-in compact and expanded templates' \
	'  package-template  Run dsw-tdk package for TEMPLATE_DIR=/path/to/template' \
 	'  transform         Expand $(COMPACT_TEMPLATE_DIR) into $(EXPANDED_TEMPLATE_DIR)' \
	'  export-translation-tree Export $(EXPANDED_TEMPLATE_DIR) into $(TRANSLATION_TREE_DIR)' \
	'  audit-translation-tree Check translation blocks for unsafe Jinja/control syntax' \
	'  sync-translation-tree Apply translations and package $(TRANSLATED_TEMPLATE_PACKAGE)' \
	'  audit-translated-template Check translated output kept expanded template structure' \
	'  compact-template  Rebuild $(EXPANDED_TEMPLATE_DIR) into $(REBUILT_TEMPLATE_DIR)' \
	'  start-ci-dsw      Start an ephemeral local DSW stack for CI render regression' \
	'  stop-ci-dsw       Stop the ephemeral local DSW stack and remove volumes' \
	'  ci-dsw-logs       Collect local DSW stack logs under outputs/ci-dsw' \
	'  render-project    Render PROJECT_UUID or $(PROJECT_REF) with $(PROJECT_RENDER_TEMPLATE_DIR)' \
	'  render-regression Run the DSW headless regression workflow using CONFIG=$(CONFIG)' \
	'  render-regression-ci Run regression against the ephemeral local DSW using CI_CONFIG=$(CI_CONFIG)'

install-dev: venv
	$(PIP) install -r config/requirements.txt

install-hooks: venv
	$(PYTHON) -m pre_commit install

compile: venv
	$(PYTHON) -m compileall -q src tests

format: venv
	$(PYTHON) -m ruff check --config config/ruff.toml --fix src tests
	$(PYTHON) -m ruff format --config config/ruff.toml src tests

format-check: venv
	$(PYTHON) -m ruff format --check --config config/ruff.toml src tests

lint: venv
	$(PYTHON) -m ruff check --config config/ruff.toml src tests

test: test-infra test-unit

test-infra: venv
	$(PYTHON) -m pytest tests/infra

test-unit: venv
	$(PYTHON) -m pytest tests/unit

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

render-regression: transform venv
	$(PYTHON) src/render_regression.py --config $(CONFIG)

render-regression-ci: transform venv
	DSW_API_URL=$${DSW_API_URL:-http://localhost:$${DSW_CI_API_PORT:-3000}/wizard-api} \
	DSW_EMAIL=$${DSW_EMAIL:-albert.einstein@example.com} \
	DSW_PASSWORD=$${DSW_PASSWORD:-password} \
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(PYTHON) src/render_regression.py --config $(CI_CONFIG)

clean:
	rm -rf outputs dist build .pytest_cache .ruff_cache
	find . -path './.venv' -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' ! -path './.venv/*' -delete
