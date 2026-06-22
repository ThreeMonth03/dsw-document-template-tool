SHELL := bash

VENV_DIR ?= .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
BOOTSTRAP_PYTHON ?= python3
PYTHON ?= $(VENV_PYTHON)
PIP := $(PYTHON) -m pip
DSW_TDK ?= $(VENV_DIR)/bin/dsw-tdk
PYTHON_LINT_PATHS ?= src tests scripts/ci/*.py

CONFIG ?= config/regression.preview.yml
CI_CONFIG ?= config/regression.ci.yml
TEMPLATE_DIR ?=
PACKAGE_OUT ?= template.zip
SOURCE_TEMPLATE_ID ?= dsw-science-europe
SOURCE_TEMPLATE_VERSION ?= 1.30.0
SOURCE_TEMPLATE_VERSION_TAG ?= v$(SOURCE_TEMPLATE_VERSION)
TRANSLATION_SOURCE_LOCALE ?= en
TRANSLATION_LOCALE ?= zh-Hant
TRANSLATION_TARGET_LANG ?= zh_Hant
WORKSPACE_TEMPLATE_NAME ?= $(SOURCE_TEMPLATE_ID)-$(SOURCE_TEMPLATE_VERSION)
TRANSLATED_TEMPLATE_ORGANIZATION_ID ?= dsw
TRANSLATED_TEMPLATE_ID ?= science-europe-zh-hant
TRANSLATED_TEMPLATE_VERSION ?= $(SOURCE_TEMPLATE_VERSION)
TRANSLATED_TEMPLATE_NAME ?= Science Europe DMP Template (zh-Hant)
TRANSLATED_WORKSPACE_TEMPLATE_NAME ?= $(TRANSLATED_TEMPLATE_ORGANIZATION_ID)-$(TRANSLATED_TEMPLATE_ID)-$(TRANSLATED_TEMPLATE_VERSION)
SCAFFOLD_TEMPLATE_ID ?= $(TRANSLATED_TEMPLATE_ID)-scaffold
SCAFFOLD_TEMPLATE_NAME ?= $(TRANSLATED_TEMPLATE_NAME) Scaffold
COMPACT_TEMPLATE_DIR ?= workspace/document-templates/compact/$(WORKSPACE_TEMPLATE_NAME)
EXPANDED_TEMPLATE_DIR ?= workspace/document-templates/expanded/$(WORKSPACE_TEMPLATE_NAME)
TRANSLATION_TREE_DIR ?= workspace/document-templates/translation/$(WORKSPACE_TEMPLATE_NAME)
FRESH_TRANSLATION_TREE_DIR ?= outputs/translation-trees/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)/fresh/$(WORKSPACE_TEMPLATE_NAME)
MERGED_TRANSLATION_TREE_DIR ?= outputs/translation-trees/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)/merged/$(WORKSPACE_TEMPLATE_NAME)
REBUILT_TEMPLATE_DIR ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/rebuilt/$(WORKSPACE_TEMPLATE_NAME)
TRANSLATED_OUTPUT_ROOT ?= outputs/document-templates/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)
TRANSLATED_EXPANDED_TEMPLATE_DIR ?= $(TRANSLATED_OUTPUT_ROOT)/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME)
TRANSLATED_TEMPLATE_PACKAGE ?= $(TRANSLATED_OUTPUT_ROOT)/$(TRANSLATED_WORKSPACE_TEMPLATE_NAME).zip
PROJECT_REF ?= workspace/projects/test-project.json
PROJECT_UUID ?= $(DSW_PROJECT_UUID)
PROJECT_RENDER_TEMPLATE_DIR ?= $(TRANSLATED_EXPANDED_TEMPLATE_DIR)
PROJECT_RENDER_FORMAT_UUID ?= 68c26e34-5e77-4e15-9bf7-06ff92582257
PROJECT_RENDER_OUTPUT ?= outputs/project-render/$(SOURCE_TEMPLATE_ID)/$(SOURCE_TEMPLATE_VERSION_TAG)/$(TRANSLATION_LOCALE)/test-project.pdf
UPSTREAM_TEMPLATE_REPOSITORY ?= https://github.com/ds-wizard/science-europe-template.git
UPSTREAM_TEMPLATE_REMOTE ?= $(if $(filter http% git@% ssh://% git://% file://%,$(UPSTREAM_TEMPLATE_REPOSITORY)),$(UPSTREAM_TEMPLATE_REPOSITORY),https://github.com/$(UPSTREAM_TEMPLATE_REPOSITORY).git)
UPSTREAM_TEMPLATE_REF ?= latest
UPSTREAM_TEMPLATE_CACHE ?= .cache/upstream/science-europe-template
# v1.0.0-v1.15.2 use the legacy parts/ layout; src/ layout starts at v1.16.0.
UPSTREAM_TEMPLATE_MIN_SUPPORTED_REF ?= v1.30.0
UPSTREAM_TEMPLATE_TEST_REFS ?= latest main $(UPSTREAM_TEMPLATE_MIN_SUPPORTED_REF)+
UPSTREAM_TEMPLATE_MIN_COMPAT_REF ?= v1.21.0
UPSTREAM_TEMPLATE_COMPAT_REFS ?= $(UPSTREAM_TEMPLATE_MIN_COMPAT_REF)+
UPSTREAM_TEMPLATE_TEST_ROOT ?= .cache/upstream-tag-tests
UPSTREAM_TEMPLATE_ARTIFACT_REFS ?= $(UPSTREAM_TEMPLATE_MIN_COMPAT_REF)+
UPSTREAM_TEMPLATE_ARTIFACT_CACHE_ROOT ?= .cache/upstream-artifacts
UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT ?= outputs/upstream-workspaces/$(SOURCE_TEMPLATE_ID)
UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION ?= 18.0
UPSTREAM_TEMPLATE_PREVIEW_STRICT ?= true

.PHONY: help venv install-dev install-hooks compile format format-check lint test test-infra test-unit verify-template verify-workspace package-template transform compact-template export-translation-tree export-fresh-translation-tree merge-translation-tree audit-translation-tree sync-translation-tree audit-translated-template list-upstream-template-tags fetch-upstream-template test-upstream-tags test-upstream-compat-tags build-upstream-artifacts render-upstream-artifact-previews start-ci-dsw stop-ci-dsw ci-dsw-logs render-project render-regression render-regression-ci clean

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
	'  verify-workspace  Run dsw-tdk verify for generated compact and expanded workspaces' \
	'  package-template  Run dsw-tdk package for TEMPLATE_DIR=/path/to/template' \
	'  transform         Expand $(COMPACT_TEMPLATE_DIR) into $(EXPANDED_TEMPLATE_DIR)' \
	'  export-translation-tree Export $(EXPANDED_TEMPLATE_DIR) into $(TRANSLATION_TREE_DIR)' \
	'  export-fresh-translation-tree Export $(EXPANDED_TEMPLATE_DIR) into $(FRESH_TRANSLATION_TREE_DIR)' \
	'  merge-translation-tree Merge $(TRANSLATION_TREE_DIR) into $(MERGED_TRANSLATION_TREE_DIR)' \
	'  audit-translation-tree Check translation blocks for unsafe Jinja/control syntax' \
	'  sync-translation-tree Apply translations and package $(TRANSLATED_TEMPLATE_PACKAGE)' \
	'  audit-translated-template Check translated output kept expanded template structure' \
	'  compact-template  Rebuild $(EXPANDED_TEMPLATE_DIR) into $(REBUILT_TEMPLATE_DIR)' \
	'  list-upstream-template-tags Show available upstream Science Europe version tags' \
	'  fetch-upstream-template Fetch upstream template into $(UPSTREAM_TEMPLATE_CACHE)' \
	'  test-upstream-tags Smoke-test transform/export/sync/package for upstream refs' \
	'  test-upstream-compat-tags Non-blocking smoke test for older compatible upstream refs' \
	'  build-upstream-artifacts Build clean multi-version workspaces and scaffold packages' \
	'  render-upstream-artifact-previews Render demo PDFs for built scaffold packages' \
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
	$(PYTHON) -m compileall -q $(PYTHON_LINT_PATHS)

format: venv
	$(PYTHON) -m ruff check --config config/ruff.toml --fix $(PYTHON_LINT_PATHS)
	$(PYTHON) -m ruff format --config config/ruff.toml $(PYTHON_LINT_PATHS)

format-check: venv
	$(PYTHON) -m ruff format --check --config config/ruff.toml $(PYTHON_LINT_PATHS)

lint: venv
	$(PYTHON) -m ruff check --config config/ruff.toml $(PYTHON_LINT_PATHS)

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

export-fresh-translation-tree: transform venv
	$(PYTHON) src/translation_tree.py export --source $(EXPANDED_TEMPLATE_DIR) --output $(FRESH_TRANSLATION_TREE_DIR)

merge-translation-tree: export-fresh-translation-tree venv
	$(PYTHON) src/translation_tree.py merge \
		--old-tree "$(TRANSLATION_TREE_DIR)" \
		--new-tree "$(FRESH_TRANSLATION_TREE_DIR)" \
		--output "$(MERGED_TRANSLATION_TREE_DIR)" \
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

list-upstream-template-tags:
	@git ls-remote --tags --refs "$(UPSTREAM_TEMPLATE_REMOTE)" "v*" \
		| awk '{ sub("refs/tags/", "", $$2); print $$2 }' \
		| sort -V

fetch-upstream-template:
	@set -euo pipefail; \
	mkdir -p "$(UPSTREAM_TEMPLATE_CACHE)"; \
	if [ ! -d "$(UPSTREAM_TEMPLATE_CACHE)/.git" ]; then \
		echo "INFO: Initializing upstream template cache at $(UPSTREAM_TEMPLATE_CACHE)"; \
		git -C "$(UPSTREAM_TEMPLATE_CACHE)" init; \
		git -C "$(UPSTREAM_TEMPLATE_CACHE)" remote add origin "$(UPSTREAM_TEMPLATE_REMOTE)"; \
	else \
		echo "INFO: Updating upstream template cache at $(UPSTREAM_TEMPLATE_CACHE)"; \
		git -C "$(UPSTREAM_TEMPLATE_CACHE)" remote set-url origin "$(UPSTREAM_TEMPLATE_REMOTE)"; \
	fi; \
	git -C "$(UPSTREAM_TEMPLATE_CACHE)" fetch --prune --tags origin '+refs/heads/*:refs/remotes/origin/*'; \
	resolved_ref="$(UPSTREAM_TEMPLATE_REF)"; \
	if [ "$$resolved_ref" = "latest" ]; then \
		resolved_ref="$$(git -C "$(UPSTREAM_TEMPLATE_CACHE)" tag -l 'v*' | sort -V | tail -n 1)"; \
	fi; \
	if [ -z "$$resolved_ref" ]; then \
		echo "ERROR: Could not resolve upstream template ref '$(UPSTREAM_TEMPLATE_REF)'." >&2; \
		exit 1; \
	fi; \
	checkout_ref="$$resolved_ref"; \
	if git -C "$(UPSTREAM_TEMPLATE_CACHE)" rev-parse --verify --quiet "origin/$$resolved_ref" >/dev/null; then \
		checkout_ref="origin/$$resolved_ref"; \
	fi; \
	git -C "$(UPSTREAM_TEMPLATE_CACHE)" checkout --force --detach "$$checkout_ref"; \
	echo "INFO: Upstream template ref $(UPSTREAM_TEMPLATE_REF) resolved to $$resolved_ref ($$(git -C "$(UPSTREAM_TEMPLATE_CACHE)" rev-parse --short HEAD))"

test-upstream-tags: venv
	@set -euo pipefail; \
	refs="$$(python3 scripts/ci/resolve_upstream_refs.py \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)" \
		$(UPSTREAM_TEMPLATE_TEST_REFS))"; \
	echo "INFO: Smoke-testing upstream refs: $$refs"; \
	for ref in $$refs; do \
		safe_ref="$$(printf '%s' "$$ref" | tr -c 'A-Za-z0-9._-' '-')"; \
		case_root="$(UPSTREAM_TEMPLATE_TEST_ROOT)/$$safe_ref"; \
		case "$$case_root" in \
			.cache/*|/tmp/*|/var/tmp/*) rm -rf "$$case_root" ;; \
			*) echo "ERROR: Refusing to clean unsafe test root $$case_root" >&2; exit 1 ;; \
		esac; \
		cache_dir="$$case_root/upstream"; \
		expanded_dir="$$case_root/expanded"; \
		tree_dir="$$case_root/translation-tree"; \
		output_dir="$$case_root/output"; \
		package_path="$$case_root/output.zip"; \
		echo "INFO: [$$ref] fetching upstream"; \
		$(MAKE) --no-print-directory fetch-upstream-template \
			UPSTREAM_TEMPLATE_REF="$$ref" \
			UPSTREAM_TEMPLATE_CACHE="$$cache_dir"; \
		version="$$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$$cache_dir/template.json")"; \
		echo "INFO: [$$ref] transform/export/sync/package version $$version"; \
		$(PYTHON) src/transform_template.py expand \
			--source "$$cache_dir" \
			--output "$$expanded_dir"; \
		$(PYTHON) src/translation_tree.py export \
			--source "$$expanded_dir" \
			--output "$$tree_dir"; \
		$(PYTHON) src/translation_tree.py sync \
			--tree "$$tree_dir" \
			--source "$$expanded_dir" \
			--output "$$output_dir" \
			--template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
			--template-id "$(TRANSLATED_TEMPLATE_ID)-smoke" \
			--template-name "$(TRANSLATED_TEMPLATE_NAME) Smoke Test" \
			--template-version "$$version"; \
		$(PYTHON) src/translation_tree.py audit-output \
			--source "$$expanded_dir" \
			--output "$$output_dir"; \
		$(DSW_TDK) verify "$$output_dir"; \
		$(DSW_TDK) package "$$output_dir" --output "$$package_path" --force; \
		echo "INFO: [$$ref] passed"; \
	done

test-upstream-compat-tags:
	$(MAKE) --no-print-directory test-upstream-tags \
		UPSTREAM_TEMPLATE_TEST_REFS="$(UPSTREAM_TEMPLATE_COMPAT_REFS)" \
		UPSTREAM_TEMPLATE_TEST_ROOT="$(UPSTREAM_TEMPLATE_TEST_ROOT)/compat"

build-upstream-artifacts: venv
	@set -euo pipefail; \
	refs="$$(python3 scripts/ci/resolve_upstream_refs.py \
		--remote "$(UPSTREAM_TEMPLATE_REMOTE)" \
		$(UPSTREAM_TEMPLATE_ARTIFACT_REFS))"; \
	echo "INFO: Building clean upstream artifacts for refs: $$refs"; \
	for ref in $$refs; do \
		safe_ref="$$(printf '%s' "$$ref" | tr -c 'A-Za-z0-9._-' '-')"; \
		cache_dir="$(UPSTREAM_TEMPLATE_ARTIFACT_CACHE_ROOT)/$$safe_ref/upstream"; \
		echo "INFO: [$$ref] fetching upstream"; \
		$(MAKE) --no-print-directory fetch-upstream-template \
			UPSTREAM_TEMPLATE_REF="$$ref" \
			UPSTREAM_TEMPLATE_CACHE="$$cache_dir"; \
		version="$$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$$cache_dir/template.json")"; \
		version_tag="v$$version"; \
		workspace_root="$(UPSTREAM_TEMPLATE_ARTIFACT_WORKSPACE_ROOT)/$$version_tag"; \
		workspace_template_name="$(SOURCE_TEMPLATE_ID)-$$version"; \
		compact_dir="$$workspace_root/compact/$$workspace_template_name"; \
		expanded_dir="$$workspace_root/expanded/$$workspace_template_name"; \
		tree_dir="$$workspace_root/translation/$$workspace_template_name"; \
		output_root="outputs/document-templates/$(SOURCE_TEMPLATE_ID)/$$version_tag/$(TRANSLATION_LOCALE)/scaffold"; \
		output_dir="$$output_root/$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)-$(SCAFFOLD_TEMPLATE_ID)-$$version"; \
		package_path="$$output_root/$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)-$(SCAFFOLD_TEMPLATE_ID)-$$version.zip"; \
		case "$$workspace_root" in outputs/*) rm -rf "$$workspace_root" ;; *) echo "ERROR: Refusing to clean unsafe workspace root $$workspace_root" >&2; exit 1 ;; esac; \
		case "$$output_root" in outputs/*) rm -rf "$$output_root" ;; *) echo "ERROR: Refusing to clean unsafe output root $$output_root" >&2; exit 1 ;; esac; \
		mkdir -p "$$(dirname "$$compact_dir")" "$$output_root"; \
		cp -a "$$cache_dir" "$$compact_dir"; \
		rm -rf "$$compact_dir/.git"; \
		commit_sha="$$(git -C "$$cache_dir" rev-parse HEAD)"; \
		python3 -c 'import json, sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps({"repository": sys.argv[2], "requested_ref": sys.argv[3], "commit_sha": sys.argv[4], "template_id": sys.argv[5], "template_version": sys.argv[6]}, indent=2) + "\n", encoding="utf-8")' \
			"$$workspace_root/upstream.json" \
			"$(UPSTREAM_TEMPLATE_REMOTE)" \
			"$$ref" \
			"$$commit_sha" \
			"$(SOURCE_TEMPLATE_ID)" \
			"$$version"; \
		echo "INFO: [$$ref] transform/export/sync/package version $$version"; \
		$(PYTHON) src/transform_template.py expand \
			--source "$$compact_dir" \
			--output "$$expanded_dir"; \
		$(PYTHON) src/translation_tree.py export \
			--source "$$expanded_dir" \
			--output "$$tree_dir"; \
		$(PYTHON) src/translation_tree.py sync \
			--tree "$$tree_dir" \
			--source "$$expanded_dir" \
			--output "$$output_dir" \
			--template-organization-id "$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)" \
			--template-id "$(SCAFFOLD_TEMPLATE_ID)" \
			--template-name "$(SCAFFOLD_TEMPLATE_NAME)" \
			--template-version "$$version"; \
		$(PYTHON) src/translation_tree.py audit-output \
			--source "$$expanded_dir" \
			--output "$$output_dir"; \
		$(DSW_TDK) verify "$$output_dir"; \
		$(DSW_TDK) package "$$output_dir" --output "$$package_path" --force; \
		echo "INFO: [$$ref] artifact package written to $$package_path"; \
	done

render-upstream-artifact-previews: venv
	@set -euo pipefail; \
	shopt -s nullglob; \
	template_dirs=(outputs/document-templates/$(SOURCE_TEMPLATE_ID)/v*/$(TRANSLATION_LOCALE)/scaffold/$(TRANSLATED_TEMPLATE_ORGANIZATION_ID)-$(SCAFFOLD_TEMPLATE_ID)-*); \
	if [ "$${#template_dirs[@]}" -eq 0 ]; then \
		echo "ERROR: No scaffold template directories found. Run make build-upstream-artifacts first." >&2; \
		exit 1; \
	fi; \
	for template_dir in "$${template_dirs[@]}"; do \
		if [ ! -d "$$template_dir" ]; then \
			continue; \
		fi; \
		version="$$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$$template_dir/template.json")"; \
		metamodel_version="$$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("metamodelVersion", ""))' "$$template_dir/template.json")"; \
		version_tag="v$$version"; \
		output_path="outputs/project-render/$(SOURCE_TEMPLATE_ID)/$$version_tag/$(TRANSLATION_LOCALE)/scaffold/test-project.pdf"; \
		if [ "$$metamodel_version" != "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" ]; then \
			skip_path="$$(dirname "$$output_path")/skipped.json"; \
			$(PYTHON) scripts/ci/write_preview_status.py \
				--output "$$skip_path" \
				--status skipped \
				--reason unsupported_metamodel_version \
				--template-version "$$version_tag" \
				--template-metamodel-version "$$metamodel_version" \
				--preview-metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)"; \
			echo "INFO: Skipping scaffold demo for $$version_tag: metamodel $$metamodel_version is not supported by preview DSW metamodel $(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)"; \
			continue; \
		fi; \
		echo "INFO: Rendering scaffold demo for $$version_tag to $$output_path"; \
		set +e; \
		$(PYTHON) src/render_project.py \
			--project-ref "$(PROJECT_REF)" \
			--template-dir "$$template_dir" \
			--format-uuid "$(PROJECT_RENDER_FORMAT_UUID)" \
			--output "$$output_path" \
			--tdk-executable "$(DSW_TDK)"; \
		render_status=$$?; \
		set -e; \
		if [ "$$render_status" -ne 0 ]; then \
			failure_path="$$(dirname "$$output_path")/failed.json"; \
			$(PYTHON) scripts/ci/write_preview_status.py \
				--output "$$failure_path" \
				--status failed \
				--reason render_failed \
				--template-version "$$version_tag" \
				--template-metamodel-version "$$metamodel_version" \
				--preview-metamodel-version "$(UPSTREAM_TEMPLATE_PREVIEW_METAMODEL_VERSION)" \
				--exit-code "$$render_status"; \
			echo "WARNING: Scaffold demo failed for $$version_tag; wrote $$failure_path"; \
			if [ "$(UPSTREAM_TEMPLATE_PREVIEW_STRICT)" = "true" ]; then \
				exit "$$render_status"; \
			fi; \
		fi; \
	done

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

render-regression-ci: venv
	DSW_API_URL=$${DSW_API_URL:-http://localhost:$${DSW_CI_API_PORT:-3000}/wizard-api} \
	DSW_EMAIL=$${DSW_EMAIL:-albert.einstein@example.com} \
	DSW_PASSWORD=$${DSW_PASSWORD:-password} \
	DSW_DOWNLOAD_HOST_ALIAS=$${DSW_DOWNLOAD_HOST_ALIAS:-host.docker.internal=localhost} \
	$(PYTHON) src/render_regression.py --config $(CI_CONFIG)

clean:
	rm -rf outputs dist build .pytest_cache .ruff_cache
	find . -path './.venv' -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' ! -path './.venv/*' -delete
