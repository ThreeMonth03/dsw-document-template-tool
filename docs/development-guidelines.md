# Development Guidelines

These rules keep the infrastructure maintainable as parser logic, supported
template versions, and downstream translation branches evolve.

## Source And Generated Files

Commit source and fixtures:

- `src/`
- `scripts/ci/`
- `config/`
- `examples/`
- `tests/`
- `docs/`
- `workspace/knowledge-models/`
- `workspace/projects/`
- `assets/fonts/`

Do not commit generated outputs:

- `outputs/`
- `.cache/`
- `workspace/document-templates/`
- Python caches
- local virtualenvs

Use `make clean` when generated files make local review noisy.

## Code Organization

- Keep root `src/*.py` files as compatibility shims.
- Put reusable behavior in `src/dsw_document_template_tool/`.
- Put GitHub Actions helpers in `scripts/ci/`.
- Keep GitHub Actions YAML thin. YAML should describe the flow; Python helpers
  should perform parsing, branching, validation, and GitHub API logic.
- Add a `--help` smoke test for every new helper in
  `tests/infra/test_cli_entrypoints.py`.
- Add focused behavior tests under `tests/infra/` or `tests/unit/` when a helper
  makes decisions.

## Parser And Translation Safety

- Prefer complete translator-facing sentences over small Jinja fragments.
- Do not expose raw `{% ... %}` or `{{ ... }}` as editable translation text.
- Keep placeholders such as `{name}` visible and audited.
- Make migration conservative. Exact source hash and executable-placeholder
  matches can be copied automatically; changed source should stay empty for
  human review.
- If a fix requires target-language word order, first check whether the expanded
  transform should produce a better translation unit.

## Release And Publication Policy

- GitHub Actions artifacts are run-scoped and temporary.
- GitHub Release assets are stable download buckets and may be overwritten by CI
  with `--clobber`.
- Release tags are not the source of truth for generated asset provenance. The
  release notes, checksums, workflow run, and asset names are.
- downstream publication or DSW import policy belongs in the downstream
  translation repository

## Standard Checks

Before pushing infra changes:

```shell
make sync-dsw-runtime-matrix
make format-check
make lint
make test
git diff --check
```

For parser, migration, release, or downstream workflow changes, also run the
targeted checks listed in the relevant runbook.
