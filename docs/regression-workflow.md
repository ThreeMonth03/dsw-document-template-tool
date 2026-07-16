# Regression Workflow

This document explains the headless render regression layer used to prove that a
template transform still behaves like the original template.

## Goal

Regression answers one question:

> Does the refactored or generated template render the same document as the
> original template for the same project answers?

The workflow does not use the DSW web client. It talks directly to the DSW API,
uploads draft templates, creates fixture projects, renders documents, and
compares normalized HTML.

## Two Independent Metamodels

DSW stores Knowledge Models and document templates as different package types.
Each type has its own `metamodelVersion`; equal-looking version numbers are not
required and must not be compared with each other.

- `config/dsw-compat.yml` maps the upstream **document-template** metamodel to a
  proven DSW server and TDK runtime. The current template ranges use `17.1` and
  `18.0`.
- The checked-in `dsw:root:2.7.0` and `dsw:root-zh-hant:2.7.0` Knowledge Model
  bundles both use KM metamodel `19`.

One immutable official KM can therefore exercise templates from more than one
document-template metamodel, provided each configured DSW runtime can import
both package types. CI proves that contract by importing the KM and rendering
the template; this repository does not derive historical KMs from PO files.

## Supported Modes

Preview mode compares local draft templates through:

```text
/document-template-drafts/{id}/documents/preview
```

Document mode compares released templates through:

```text
POST /documents
```

Draft preview mode is the default for baseline/candidate regression because it
does not require publishing candidate template versions. Clean scaffold and
translated-template delivery checks instead import the newly built package ZIP
before rendering, so CI validates the same artifact that users download.

## Fixture Strategy

Fixtures use the same logical shape as DSW projects:

- a knowledge-model package reference
- a stable list of project events
- a render request using a document template

An `events_file` fixture renders the project's complete current state after the
bulk import. Set `project_event_uuid` only when intentionally testing an
existing historical snapshot; CI never infers a snapshot by sorting imported
events because DSW may assign the same timestamp to the whole batch.

When a local `.km` bundle contains package history, the render client resolves
the exact top-level package ID declared by the bundle. It must not fall back to
an older package merely because an older DSW API returns that package first. A
strict preview fails if the requested package cannot be imported by the
selected runtime.

The repo keeps project fixtures under `fixtures/projects/` and immutable
Knowledge Model bundles under `fixtures/knowledge-models/`. Baseline/candidate
regression uses the official `dsw:root:2.7.0` bundle because that is a package
family declared by the upstream Science Europe template. The zh-Hant bundle is
reserved for translated demo/PDF review. CI can recreate both kinds of project
in an ephemeral local DSW stack without rebuilding a KM from PO files or
depending on a live Registry download.

For broad regression coverage, generated fixtures ask the DSW API for the
compiled questionnaire model and produce deterministic event payloads. Before
creating projects, the planner generates a larger in-memory candidate pool and
greedily selects the smallest useful subset within the configured case limit.
Coverage includes every reachable option answer, list cardinality, and
multi-choice shape. The checked-in CI config requires complete coverage for
every version selected by the compatibility plan.

Each generated group writes `<name-prefix>-coverage.json` beside its regression
report. It records selected case indexes, coverage totals by category, and any
missing branches. Candidate generation is local and cheap; only selected cases
become DSW projects and render comparisons.

GitHub Actions runs
[`summarize_regression_coverage.py`](../scripts/ci/summarize_regression_coverage.py)
after regression even when the regression step fails. The run summary shows
each version, comparison result, rendered fixture count, selected
generated cases, and covered/expected branch count. The summary is diagnostic;
the regression command remains the pass/fail gate.

## Local Commands

Run the same local sequence that CI uses for preview regression:

```shell
make build-upstream-artifacts
make generate-compat-ledger
make start-ci-dsw
make render-regression-ci-plan
make summarize-regression-coverage
make ci-dsw-logs
make stop-ci-dsw
```

`make build-upstream-artifacts` must run first. It fetches the upstream template
refs and creates versioned baseline and candidate directories under
`outputs/upstream-workspaces/...`. `generate-compat-ledger` writes the
regression candidate plan. `render-regression-ci-plan` reads that plan,
generates one versioned config per recommended version, and runs DSW regression
without overwriting preview artifacts from other versions. It fails if the plan
does not recommend a candidate for the selected metamodel; it never substitutes
an unrelated `latest` version. The regression command is therefore
intentionally not standalone on a clean checkout.

## Compatibility Ledger

`make generate-compat-ledger` is the fast offline layer between scaffold
generation and full DSW rendering. It reads the generated workspaces under
`outputs/upstream-workspaces/...` and writes:

- `outputs/compat-ledger/<template-id>/summary.md`
- `outputs/compat-ledger/<template-id>/index.json`
- `outputs/compat-ledger/<template-id>/vX.Y.Z.json`
- `outputs/compat-ledger/<template-id>/regression-plan.md`
- `outputs/compat-ledger/<template-id>/regression-plan.json`

The ledger records file-tree digests, expanded generated-block counts,
translation-tree unit counts, placeholder inventories, and scaffold package
checksums for every built upstream version. Use it to spot cross-version drift
before spending CI time on DSW preview/PDF rendering.

The regression plan recommends high-value candidates: the first and latest
version for each metamodel runtime, plus any version whose expanded/tree
structure signature changed within the same metamodel. Every recommended
candidate runs the same complete branch-coverage gate from the base config.
Versions with unchanged structural signatures are omitted from DSW regression
rather than tested with a weaker partial profile; the compatibility ledger
still records and compares every built version.

This policy spends DSW render time only on structurally meaningful versions
without weakening the evidence for versions that are selected.

In GitHub Actions, `make generate-compat-ledger` also appends both reports to
the step summary, so maintainers can review the drift and candidate plan before
downloading artifacts.

The ledger is not a substitute for render regression. It proves that generated
files and translator-facing trees have stable fingerprints; only the DSW
regression jobs prove that those templates still render correctly through the
DSW API.

If ports conflict locally:

```shell
export DSW_CI_API_PORT=3100
export DSW_CI_MINIO_PORT=9100
export DSW_API_URL=http://localhost:3100/wizard-api
export DSW_EMAIL=albert.einstein@example.com
export DSW_PASSWORD=password
```

Run regression against a custom config:

```shell
make render-regression CONFIG=config/regression.preview.yml
```

The same rule applies to custom configs: if their `subjects` point at
`outputs/upstream-workspaces/...`, build those artifacts before rendering.

To debug an older built version instead of the latest one, pass an explicit
version to the single-version target:

```shell
make render-regression-ci UPSTREAM_TEMPLATE_REGRESSION_VERSION=v1.30.0
```

## CI Shape

The GitHub Actions workflow is:

- `.github/workflows/headless_render_regression.yml`

It has two jobs:

- `offline-checks`: install dependencies, smoke-test upstream refs, discover DSW
  compatibility, run format/lint/tests.
- `render-regression`: run a metamodel-aware DSW matrix, build clean scaffold
  artifacts, run full regression and strict demo previews for every supported
  runtime, and upload artifacts.

The runtime matrix comes from:

- `config/dsw-compat.yml`

The checked-in workflow contains a generated matrix block. After changing the
compatibility table, run `make sync-dsw-runtime-matrix` instead of editing that
block by hand.

Current policy:

| Template range | DSW runtime | Full baseline/candidate regression | Strict demo preview |
| --- | --- | --- | --- |
| `v1.29.1` | DSW 4.26 | Required | Required |
| `v1.30.0+` | DSW 4.30 | Required | Required |

A row in `config/dsw-compat.yml` means that both checks are required. Do not add
per-runtime skip flags: a runtime that cannot pass the common contract is not a
supported runtime yet.

If a future upstream tag introduces a new `metamodelVersion`, CI should fail
clearly during compatibility discovery. The failure summary includes an
advisory runtime hint from the official DSW document-template metamodel notes.
Add a new runtime only after verifying the matching DSW server and TDK versions.

## Outputs

Regression artifacts are generated under `outputs/` and uploaded by CI. They are
not committed to the repository's default branch.

Important output families:

- `outputs/upstream-workspaces/...`: clean compact, expanded, and translation
  scaffolds for each upstream version.
- `outputs/compat-ledger/...`: offline cross-version fingerprints and regression
  candidate plans for compact, expanded, expanded-regression, translation-tree,
  and scaffold package outputs.
- `outputs/document-templates/...`: packaged scaffold templates.
- `outputs/project-render/...`: demo PDFs or `skipped.json` / `failed.json`
  preview status files.
- `outputs/preview/...`: raw and normalized HTML, diffs, fixture events, and
  regression reports, including generated branch-coverage reports.

On non-PR runs, CI also stages the clean scaffold package, clean upstream
workspace bundle, preview bundle, release notes, and `SHA256SUMS` under
`outputs/release-assets/...`, then uploads them to a prerelease GitHub Release
named like `clean-scaffold-dsw-science-europe-v1.30.1`.

Those releases are convenience download buckets for public repository
maintenance. They are not finished public translations.
