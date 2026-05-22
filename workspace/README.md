## Workspace

This folder keeps the translation workflow assets in one place:

- `knowledge-models/`
  stores KM bundles used by fixture projects and CI regression
- `document-templates/compact/`
  stores the original DSW-uploadable template trees
- `document-templates/expanded/`
  stores translation-friendly expanded Jinja workspaces generated from the
  compact templates, with sentence-preserving generated Jinja comment markers
- `document-templates/translation/`
  stores translator-facing unit trees exported from `expanded/`, with one
  `translation.md` file per preserved translation unit

Run `make transform` to refresh the expanded workspace from the compact source.
Run `make export-translation-tree` to refresh the translator-facing tree from
the expanded workspace.
Run `make sync-translation-tree` to apply translator edits back into a generated
expanded template copy.
Run `make compact-template` when you need to rebuild an uploadable compact tree
from the expanded workspace.
