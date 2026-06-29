# Parser And Translation Tree

Use this runbook when changing sentence extraction, marker placement, Markdown
translation files, migration, sync, or output structure audits.

## Pipeline

```text
compact template
  -> expanded template with translation markers
  -> translator-facing translation tree
  -> translated expanded template
  -> packaged DSW document template
```

The key goal is to give translators complete, editable units without changing
the executable Jinja behavior of the original template.

## What Belongs Where

- Template-specific Jinja rewrite logic belongs under
  `_template_transform/science_europe*.py`.
- Generic marker, branch, and inline conditional behavior belongs under
  `_template_transform/`.
- Translation Markdown format and metadata belongs under `_translation_tree/`.
- Cross-version translation reuse belongs in `_translation_tree/merge.py` and
  `translation_migration.py`.
- Target-language output cleanup belongs in `_translation_tree/output_polish.py`.

Do not fix broken sentence boundaries by hand-editing generated
`translation.md` files. Fix the transform/export logic and regenerate.

## Translation Unit Quality Rules

Good units:

- contain a complete sentence, heading, paragraph, list item, or branch-complete
  sentence group
- allow placeholders to be reordered
- hide machine metadata below the editable text
- avoid raw Jinja in translator-editable blocks

Bad units:

- split a sentence around an `if` or `elif`
- combine unrelated independent sentences into a Cartesian explosion
- expose branch separators such as `/` as something translators must preserve
- require translators to understand Jinja scope to translate safely

## Changing Parsing Logic

1. Add or update transform/export tests.
2. Run:

   ```shell
   make format-check
   make lint
   make test
   ```

3. Build clean upstream artifacts:

   ```shell
   make build-upstream-artifacts
   ```

4. Generate a fresh tree and merge existing translations exactly:

   ```shell
   make export-fresh-translation-tree
   make merge-translation-tree
   ```

5. Inspect generated `outline.md`, `merge-report.json`, and representative
   `translation.md` files.
6. Sync translations and render a demo PDF.
7. Confirm no translator-facing files contain raw Jinja or unnatural fragments.

## Migration After Parser Changes

Parser changes can invalidate old translation paths and hashes. The migration
policy is intentionally conservative:

- exact source hash and executable-placeholder matches may reuse translations
- non-exact matches stay empty and require review
- sentence-match suggestions should be treated as review hints, not automatic
  truth

When a parser change is broad, refresh downstream `translation/v*` branches with
clean scaffold artifacts and inspect what became untranslated before asking
translators to continue.

## Audits To Trust

- `translation_tree.py audit` catches unsafe translator-facing blocks.
- `translation_tree.py sync` catches missing or changed placeholders.
- `translation_tree.py audit-output` catches executable Jinja, HTML wiring,
  asset, link, or static source drift.
- Render previews catch runtime DSW/TDK/template integration issues.

No single audit proves translation wording is good. Downstream translation
repositories should review wording, glossary, and layout against their own QA
checklist.

## Known zh-Hant Output Concerns

- Some upstream templates use `|dot`. In zh-Hant output, leftover `|dot` can
  create duplicate punctuation after Chinese sentences. The sync output polish
  step removes unsafe leftover `|dot` behavior.
- CJK font behavior differs from the English template. Avoid layout changes
  unless PDF QA shows a structural problem.
- Do not force Markdown list styling changes unless the rendered PDF clearly
  loses semantic list structure.
