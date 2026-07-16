# Project Fixtures

This directory contains checked-in DSW project fixtures. They all use the same
basic shape: a project reference JSON may point at an exported project events
payload, and regression configs may also reference an events payload directly.

## Layout

- [`knowledge-models/`](knowledge-models/)
  contains immutable Knowledge Model bundles referenced by checked-in project
  fixtures.
- [`projects/demo/`](projects/demo/)
  contains the human-readable sample project used for translated template
  preview PDFs and release assets.
- [`projects/regression/`](projects/regression/)
  contains small, stable fixtures for CI behavior checks.

The demo project is intentionally useful for review, but it is still test data:
avoid putting private or production answers here. Regression fixtures should be
small and focused enough that a future maintainer can tell what behavior they
protect.

## Knowledge Model Roles

The two checked-in bundles have deliberately different responsibilities:

| Bundle | Package ID | Used for |
| --- | --- | --- |
| [`root-2.7.0.km`](knowledge-models/root-2.7.0.km) | `dsw:root:2.7.0` | Baseline/candidate structural regression against the package family declared by the upstream Science Europe template |
| [`root-zh-hant-2.7.0.km`](knowledge-models/root-zh-hant-2.7.0.km) | `dsw:root-zh-hant:2.7.0` | Translated zh-Hant demo project and PDF review |

`root-2.7.0.km` is an export of the official
[`dsw:root:2.7.0`](https://registry.ds-wizard.org/knowledge-models/dsw%3Aroot%3A2.7.0)
Registry package. Its SHA-256 is
`aabca6f7de8ad41cf9989afd25d4827f3de134fb8f0d965fcc6c336cfeb3e965`.
Keep the bundle checked in so regression remains deterministic and does not
depend on Registry availability. Do not rebuild it from translation PO files.
Its machine-readable provenance and runtime assignments are pinned in
[`config/regression-evidence.yml`](../config/regression-evidence.yml); update
that config intentionally whenever the immutable fixture changes.

## Current Fixtures

- [`projects/regression/empty-project.events.json`](projects/regression/empty-project.events.json)
  proves the render pipeline can create and render a project from a bare event
  list with no answers.
- [`projects/regression/wrapped-empty-project.events.json`](projects/regression/wrapped-empty-project.events.json)
  proves the render pipeline also accepts the exported `{ "events": [...] }`
  payload shape.
- [`projects/demo/test-project.events.json`](projects/demo/test-project.events.json)
  exercises a realistic, filled questionnaire built from public depositar RDM
  Basics material. CI uses it as `filled-demo-project` so preview regressions do
  not only cover the empty questionnaire.
- `generated_fixtures` in
  [`config/regression.ci.yml`](../config/regression.ci.yml)
  plans deterministic branch-sweeping projects during CI. It searches a large
  local candidate pool, renders only a compact selected set, and writes a
  coverage report under `outputs/preview/`. Generated events are not committed
  because they are mechanically derived.

When adding fixtures, prefer several focused payloads over one huge payload,
especially for list cardinalities (`0`, `1`, `2`, `3+`) and mutually exclusive
answer branches.
