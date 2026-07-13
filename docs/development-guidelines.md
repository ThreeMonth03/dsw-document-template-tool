# Development Guidelines

These rules keep the infrastructure maintainable as parser logic, supported
template versions, and public repository `sync/v*` branches evolve.

## Source and Generated Files

Commit source and fixtures:

- `src/`
- `scripts/ci/`
- `pyproject.toml`
- `config/`
- `examples/`
- `tests/`
- `docs/`
- `fixtures/`
- `assets/fonts/`

Do not commit generated outputs:

- `outputs/`
- `.cache/`
- `workspace/document-templates/`
- Python caches
- local virtualenvs

Use `make clean` when generated files make local review noisy.

## Code Organization

- Put reusable behavior in
  [`src/dsw_document_template_tool/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool).
- Put maintained direct CLI entrypoints in
  [`src/dsw_document_template_tool/cli/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/src/dsw_document_template_tool/cli).
- Expose user-facing CLI commands through
  [`pyproject.toml`](https://github.com/ThreeMonth03/dsw-document-template-tool/blob/master/pyproject.toml).
- Put GitHub Actions helpers in
  [`scripts/ci/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/scripts/ci).
- Keep GitHub Actions YAML thin. YAML should describe the flow; Python helpers
  should perform parsing, branching, validation, and GitHub API logic.
- Add a `--help` smoke test for every new helper in
  `tests/infra/test_cli_entrypoints.py`.
- Add focused behavior tests under `tests/infra/` or `tests/unit/` when a helper
  makes decisions.

## Parser and Translation Safety

- Prefer complete translator-facing sentences over small Jinja fragments.
- Do not expose raw `{% ... %}` or `{{ ... }}` as editable translation text.
- Keep placeholders such as `{name}` visible and audited.
- Make migration conservative. Exact source hash and executable-placeholder
  matches can be copied automatically; changed source should stay empty for
  human review.
- If a fix requires target-language word order, first check whether the expanded
  transform should produce a better translation unit.

## Release and Publication Policy

- GitHub Actions artifacts are run-scoped and temporary.
- GitHub Release assets are stable download buckets and may be overwritten by CI
  with `--clobber`.
- Release tags are not the source of truth for generated asset provenance. The
  release notes, checksums, workflow run, and asset names are.
- Translated release and DSW import policy belongs in the public
  translated-template repository.
- If the public repository combines translation work and release assets, draft
  `sync/v*` branches, PRs, logs, and artifacts may be visible. Use the
  copy-ready docs in
  [`examples/translation-repository/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples/translation-repository)
  to document that local policy.

## Standard Checks

Before pushing infra changes:

```shell
make sync-dsw-runtime-matrix
make check
git diff --check
```

For parser, migration, release, or public-repository workflow changes, also run the
targeted checks listed in the relevant runbook.
