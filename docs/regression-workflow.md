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

## Supported Modes

Preview mode compares local draft templates through:

```text
/document-template-drafts/{id}/documents/preview
```

Document mode compares released templates through:

```text
POST /documents
```

Preview mode is the default for template refactoring and translation scaffold
checks because it does not require publishing candidate template versions.

## Fixture Strategy

Fixtures use the same logical shape as DSW projects:

- a knowledge-model package reference
- a stable list of project events
- a render request using a document template

The repo keeps project fixtures under `fixtures/projects/` and the checked-in KM
bundle under `fixtures/knowledge-models/`. CI can recreate those projects in an
ephemeral local DSW stack, render PDFs, and upload previews as artifacts.

For broad regression coverage, generated fixtures ask the DSW API for the
compiled questionnaire model and produce deterministic event payloads. The
checked-in CI config uses an empty smoke fixture, the filled demo fixture, and
fixed-seed generated fixtures.

## Local Commands

Run the same local sequence that CI uses for preview regression:

```shell
make build-upstream-artifacts
make start-ci-dsw
make render-regression-ci
make ci-dsw-logs
make stop-ci-dsw
```

`make build-upstream-artifacts` must run first. It fetches the upstream template
refs and creates the generated baseline and candidate directories under
`outputs/upstream-workspaces/...`. The checked-in regression configs point at
those generated directories, so `render-regression-ci` is intentionally not a
standalone command on a clean checkout.

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

## CI Shape

The GitHub Actions workflow is:

- `.github/workflows/headless_render_regression.yml`

It has two jobs:

- `offline-checks`: install dependencies, smoke-test upstream refs, discover DSW
  compatibility, run format/lint/tests.
- `render-regression`: run a metamodel-aware DSW matrix, build clean scaffold
  artifacts, render demo previews, and upload artifacts.

The runtime matrix comes from:

- `config/dsw-compat.yml`

The checked-in workflow contains a generated matrix block. After changing the
compatibility table, run `make sync-dsw-runtime-matrix` instead of editing that
block by hand.

Current policy:

- `v1.29.1` uses the DSW 4.26 runtime.
- `v1.30.0+` uses the DSW 4.30 runtime.

If a future upstream tag introduces a new `metamodelVersion`, CI should fail
clearly during compatibility discovery. The failure summary includes an
advisory runtime hint from the official DSW document-template metamodel notes.
Add a new runtime only after verifying the matching DSW server and TDK versions.

## Outputs

Regression artifacts are generated under `outputs/` and uploaded by CI. They are
not committed to `master`.

Important output families:

- `outputs/upstream-workspaces/...`: clean compact, expanded, and translation
  scaffolds for each upstream version.
- `outputs/document-templates/...`: packaged scaffold templates.
- `outputs/project-render/...`: demo PDFs or `skipped.json` / `failed.json`
  preview status files.
- `outputs/preview/...`: raw and normalized HTML, diffs, fixture events, and
  regression reports.

On non-PR runs, CI also stages the clean scaffold package, clean upstream
workspace bundle, preview bundle, release notes, and `SHA256SUMS` under
`outputs/release-assets/...`, then uploads them to a prerelease GitHub Release
named like `clean-scaffold-dsw-science-europe-v1.30.1`.

Those releases are convenience download buckets for downstream translation
maintenance. They are not finished public translations.
