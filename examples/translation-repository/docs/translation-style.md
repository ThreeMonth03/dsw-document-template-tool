# Translation Terminology and Style

Use this page as a project-specific entry point for translation decisions. Do
not leave instructions such as "follow the glossary" without linking the
actual, version-controlled glossary.

## Sources of Truth

Record the project's sources in this order:

1. Shared DSW terminology maintained by the target-language DSW locale.
2. The reviewed glossary committed to this repository.
3. Existing translations in the newest reviewed version branch.
4. Contextual judgment for terms that cannot be translated mechanically.

When two sources disagree, document the chosen wording and its context here or
in the glossary. A glossary entry is guidance for meaning, not permission to
replace every matching English phrase without reading the sentence.

## Style Rules

- Write natural target-language sentences instead of preserving English word
  order.
- Keep product names, standards, identifiers, and established abbreviations
  unchanged unless the glossary explicitly provides a localized form.
- Keep every placeholder, but reorder placeholders when grammar requires it.
- Do not add raw Jinja to translator-editable blocks.
- Review punctuation after optional placeholders and conditional fragments in
  the rendered PDF, not only in Markdown.
- Reuse reviewed wording across versions only when the migration audit confirms
  that the executable source structure is compatible.

## Project Glossary

Replace this section after copying the template. Link the repository's actual
glossary and state whether entries are approved, provisional, or contextual.
If the project has no glossary yet, say so explicitly and create one before
claiming terminology consistency in QA.
