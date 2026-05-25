## Usage

### What This Tool Solves

This repository is for template authors who want to validate DSW document
template refactors in CI without running the browser client.

The workflow is intentionally headless:

- `dsw-tdk` manages local template projects and uploads draft templates
- the DSW API creates fixture projects and requests previews/documents
- this tool downloads the rendered output and compares normalized HTML

The primary goal is to answer one question safely:

> Does the refactored template behave the same as the original template?

### Translation Workspace

This repository now keeps translation assets directly in:

- `workspace/knowledge-models/`
- `workspace/document-templates/compact/`
- `workspace/document-templates/expanded/`
- `workspace/document-templates/translation/`

The checked-in `compact` tree is the original DSW-uploadable template.
The checked-in `expanded` tree is the machine-facing Jinja workspace that keeps
the original file structure and marks translatable regions with generated Jinja
comments. Those markers preserve larger units such as headings, paragraphs,
list items, and cross-branch sentence groups so later string extraction can work
on whole sentences instead of fragmented `if/else` shards. They are comments
rather than `{% set %}` captures, so they do not change Jinja variable scope.

The checked-in `translation` tree is the human-facing collaboration layer.
It exports one `translation.md` file per preserved translation unit, with separate
`Source (en)` and `Translation (zh_Hant)` sections, and can sync translator
edits back into a generated `expanded` template copy.

That makes the template reversible:

- `compact` -> `expanded` with `make transform`
- `expanded` -> `translation` with `make export-translation-tree`
- `translation` -> translated `expanded` with `make sync-translation-tree`
- `expanded` -> uploadable `compact` output with `make compact-template`

### Supported Regression Modes

- `preview` mode:
  compares two draft templates through
  `/document-template-drafts/{id}/documents/preview`
- `document` mode:
  compares two released templates through `POST /documents`

For day-to-day template refactoring, `preview` mode is the recommended default.
It works well before release and does not require publishing candidate versions.

### Important Constraint

If you compare two local directories that originate from the same template
coordinates, this tool stages them under temporary draft IDs automatically
before upload. That means you can compare a pre-refactor tree and a
post-refactor tree side by side without manually rewriting `template.json`.

### For Template Authors

#### 1. Install The Tooling Once

```shell
make install-dev
```

#### 2. Prepare A Regression Config

Start from one of the shipped workflow configs:

- `config/regression.ci.yml`
- `config/regression.preview.yml`
- `config/regression.document.yml`

The most common setup is:

- `baseline` = original local template directory
- `candidate` = refactored local template directory
- `fixtures` = one or more project-event payloads that exercise critical branches
- `generated_fixtures` = optional deterministic random projects generated from
  DSW's compiled questionnaire model

`config/regression.ci.yml` is for the checked-in GitHub Actions workflow. It
talks to an ephemeral local DSW stack started by `make start-ci-dsw` and uses
the default local admin account (`albert.einstein@example.com` / `password`).
No GitHub secret is required for that path.

`config/regression.preview.yml` is for connecting to an already-running DSW
instance. It uses environment variables for values that vary between
environments:

- `DSW_API_URL`
- `DSW_API_KEY`

When you run `config/regression.document.yml`, also set:

- `DSW_BASELINE_TEMPLATE_ID`
- `DSW_CANDIDATE_TEMPLATE_ID`

By default the shipped configs already point at:

- `../workspace/knowledge-models/root-zh-hant-2.7.0.km` from the config directory
- `../workspace/document-templates/compact/dsw-science-europe-1.30.0`
- `../workspace/document-templates/expanded/dsw-science-europe-1.30.0`
- `../workspace/document-templates/translation/dsw-science-europe-1.30.0`

The shipped CI config keeps one `empty-project` fixture and adds 80 deterministic
branch-sweeping fixtures with seed `20260522`. Those fixtures ask the local DSW
API for the compiled questionnaire model, generate realistic `SetReplyEvent`
payloads for options, lists, values, integrations, multi-choice questions, and
item-select questions where possible, and then render both templates against the
same generated answers. Nested follow-up questions use a local branch index, so
child questions keep cycling through their own answers instead of getting stuck
on the same parent-case parity.

Knowledge-model package references can still be any of:

- a package UUID
- `org:km:version`
- a local `.km` bundle path

If you pass a local `.km` bundle path, the tool first tries to match an
already-installed package with the same coordinates. If none exists, it uploads
the bundle to DSW automatically and uses the returned package UUID.

#### 3. Refresh The Expanded Machine Workspace

```shell
make transform
```

This regenerates the checked-in `expanded` tree from the checked-in `compact`
template source. The generated workspace keeps:

- the original `.j2` files in place
- generated `__tr_block_####` comment markers around translatable units
- a generated workspace `README.md`
- the upstream template readme as `UPSTREAM-README.md`

CI runs the same command and fails if the committed expanded workspace is stale
or if new expanded files were generated but not checked in.

#### 4. Refresh The Translator-Facing Tree

```shell
make export-translation-tree
```

This exports one `translation.md` file per preserved translation unit under
`workspace/document-templates/translation/`.

Each translation file contains:

- machine-exported source Jinja in `Source (en)`
- translator-edited target Jinja in `Translation (zh_Hant)`
- metadata linking the unit back to its source file and wrapper

If the tree already exists, unchanged unit translations are preserved by unit
key when you re-export it.

#### 5. Sync Translator Edits Back Into A Generated Template Copy

```shell
make sync-translation-tree
```

This writes a translated expanded workspace under:

- `outputs/document-templates/translated-expanded/`

Blank translation sections fall back to the exported English source unit, so an
untranslated tree still syncs back to the original expanded template.

#### 6. Rebuild The Pre-Translation Compact Candidate For Regression

```shell
make compact-template
```

This writes the uploadable regression candidate under:

- `outputs/document-templates/rebuilt/`

This command strips the generated `__tr_block_####` comment markers and restores the
upstream `README.md`. It exists so CI can verify that the machine-facing
`expanded` workspace still compacts back to the original template before any
translation is applied.

The unit test suite also runs deterministic exhaustive fuzz checks with a fixed
seed (`20260522`). The seed only controls the stable execution order; the test
systematically enumerates 9,072 branch contexts and renders each context through
six Jinja shapes, for 54,432 logical shape checks. Those checks exercise
`if`/`elif`/`else`, `for`/`else`, `0/1/2/3+` list cardinalities, branch-closed
HTML, nested lists, `{% set %}`, and `{% do %}` mutations, then verify that
compact and expanded renders are identical. Rendering is chunked across a
process pool in CI to keep the stronger coverage cheap.

#### 7. Run The Regression Workflow

```shell
make render-regression CONFIG=config/regression.preview.yml
```

If the normalized HTML is identical for every fixture, the command exits
successfully. When a mismatch is found, the command exits non-zero and writes:

- raw rendered HTML for each side
- normalized HTML for each side
- generated fixture events and coverage stats for random fixtures
- unified diff files
- `regression_report.json`

By default these artifacts are written under the configured `output_dir`.

#### 8. Verify Or Package A Template Manually

```shell
make verify-template TEMPLATE_DIR=/path/to/template
make verify-workspace
make package-template TEMPLATE_DIR=/path/to/template PACKAGE_OUT=template.zip
```

These targets call `dsw-tdk` directly. `verify-workspace` checks both the
checked-in compact template and the generated expanded workspace before render
regression starts.

### Fixture Strategy

This repository expects fixture data in the same logical shape used by DSW:

- create a project from a released knowledge-model package reference
- apply a stable list of project events via `PUT /projects/{uuid}/content`
- render the template against that fixture project

For `document` mode you can choose either of these fixture styles:

- define `project` plus `events_file`, and let the tool resolve the latest
  `project_event_uuid` automatically after applying the events
- define `project_uuid` plus `project_event_uuid` directly when you want to pin
  an already-existing snapshot

Each fixture should cover one meaningful branch combination. For example:

- happy path with minimal answers
- external ownership path
- optional section omitted
- repeated item list populated

Do not rely on only one fixture if the template contains branching language.
For CI, prefer `generated_fixtures` for broad randomized coverage and keep a few
hand-authored `fixtures` for exact bug reproductions or domain-specific paths.

### Recommended CI Shape

The most practical CI pipeline is:

1. run offline checks that regenerate `expanded` and `translation`
2. verify the checked-in compact and expanded templates with `dsw-tdk`
3. run unit tests, including the exhaustive transform render matrix
4. start an ephemeral local DSW stack
5. run this regression tool in `preview` mode against that local API

The tool itself does not require the DSW web client. The shipped CI stack starts
only PostgreSQL, MinIO, DSW server, and DSW document worker. It then logs in with
the default local DSW administrator, uploads the local KM/template fixtures, and
compares the rendered preview output.

Useful local commands for the CI render layer are:

```shell
make start-ci-dsw
make render-regression-ci
make ci-dsw-logs
make stop-ci-dsw
```

If ports `3000` or `9000` are already in use locally, override them while
keeping the regression config pointed at the same API port:

```shell
export DSW_CI_API_PORT=3100
export DSW_CI_MINIO_PORT=9100
export DSW_API_URL=http://localhost:3100/wizard-api
export DSW_EMAIL=albert.einstein@example.com
export DSW_PASSWORD=password
```

In the shipped setup, preview regression compares:

- baseline = checked-in `compact` template
- candidate = checked-in `expanded` template
- fixtures = one empty project plus 80 fixed-seed random questionnaire projects

### GitHub Actions Workflow

See:

- `.github/workflows/headless_render_regression.yml`

The workflow has two jobs:

- `offline-checks` runs without Docker or DSW credentials
- `render-regression` starts a temporary local DSW with Docker Compose and does
  not use GitHub Actions secrets

If you switch the workflow to `config/regression.document.yml`, you also need:

- `DSW_BASELINE_TEMPLATE_ID`
- `DSW_CANDIDATE_TEMPLATE_ID`

### For Developers

#### Show Available Targets

```shell
make help
```

#### Remove Generated Outputs And Caches

```shell
make clean
```

This removes generated artifacts such as `outputs/`, pytest/Ruff caches, and
`__pycache__` directories without touching the checked-in `workspace/` trees.

#### Install Dev Tools

```shell
make install-dev
```

#### Install Git Hooks

```shell
make install-hooks
```

#### Auto-Format Python Code

```shell
make format
```

#### Check Formatting

```shell
make format-check
```

#### Check Python Syntax

```shell
make compile
```

#### Run Lint

```shell
make lint
```

#### Run Tests

```shell
make test
```
