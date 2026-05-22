# Translation Tree

This folder is the translator-facing tree exported from the expanded
template workspace.

- Each translation unit has its own `translation.md` file.
- Each file starts with a plain `Sentence (en)` section for
  translator review, followed by the original Jinja source.
- Wrapper-level blocks from the expanded workspace are split into smaller
  translator-facing units whenever the source structure allows it.
- Edit only `Translation (zh_Hant)` sections.
- `Source (en)` sections are the machine-exported source of truth.
- Run `make sync-translation-tree` to apply translator edits back into a
  generated template copy.
