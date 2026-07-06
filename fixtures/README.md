# Project Fixtures

This directory contains checked-in DSW project fixtures. They all use the same
basic shape: a project reference JSON may point at an exported project events
payload, and regression configs may also reference an events payload directly.

## Layout

- [`knowledge-models/`](knowledge-models/)
  contains Knowledge Model bundles referenced by checked-in project fixtures.
- [`projects/demo/`](projects/demo/)
  contains the human-readable sample project used for translated template
  preview PDFs and release assets.
- [`projects/regression/`](projects/regression/)
  contains small, stable fixtures for CI behavior checks.

The demo project is intentionally useful for review, but it is still test data:
avoid putting private or production answers here. Regression fixtures should be
small and focused enough that a future maintainer can tell what behavior they
protect.

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
  creates deterministic branch-sweeping projects during CI. These generated
  fixtures are not committed because they are large and mechanically derived.

When adding fixtures, prefer several focused payloads over one huge payload,
especially for list cardinalities (`0`, `1`, `2`, `3+`) and mutually exclusive
answer branches.
