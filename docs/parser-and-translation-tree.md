# Parser and Translation Tree

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
- XLIFF exchange belongs under `_translation_tree/xliff.py`; keep it as a thin
  adapter around the canonical Markdown tree.
- Cross-version translation reuse belongs in `_translation_tree/merge.py` and
  `translation_repository/`.
- Target-language output cleanup belongs in `_translation_tree/output_polish.py`.
- Named source-preview regression guards belong in
  `_translation_tree/source_quality_rules.py`; they must not mutate executable
  template source.

Do not fix broken sentence boundaries by hand-editing generated
`translation.md` files. Fix the transform/export logic and regenerate.

## Adding an Upstream Rewrite

Use a profile rule only when generic Jinja/HTML parsing cannot preserve a
complete translation unit.

1. Confirm the template identity in `template.json`. Science Europe-only rules
   belong in `science_europe_balanced_rules.py` or
   `science_europe_unbalanced_rules.py`, not a generic parser module.
2. Add the smallest reversible replacement to a named
   `ReversibleReplacementGroup`. Give it a stable `group_id` and a rationale
   that explains the upstream shape it handles.
3. Use the balanced phase when every generated branch is syntactically valid;
   use the unbalanced phase only when the original source crosses an HTML/Jinja
   boundary.
4. Add forward, reverse, and wrong-template-identity tests. A `demo:sample`
   template must not receive a Science Europe rewrite.
5. Run `make transform` followed by `make explain-transform`. Inspect the
   profile, rule IDs, files, and match counts. The same evidence is stored in
   `.transform/manifest.json` under `rewrite_trace`.
6. Complete the parser-change checklist below and render regression before
   accepting the rule.

If executable source is correct but a sentence preview exposes a known broken
fragment, add a named `SourceFragmentRule` instead. This is an audit guard, not
a substitute for fixing extraction.

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

Static strings inside Jinja are editable only when the parser can show that
they feed rendered output. For example, a string-list initializer is exported
when the same collection is later rendered through `|join`; an otherwise
identical internal list remains machine code. Keep this data-flow check in
[`jinja_literals.py`](../src/dsw_document_template_tool/_template_transform/jinja_literals.py)
and its marker placement in
[`template_transform.py`](../src/dsw_document_template_tool/template_transform.py).
Do not replace it with variable-name, template-version, or source-sentence
special cases.

## Changing Parsing Logic

1. Add or update transform/export tests.
2. Run:

   ```shell
   make check
   ```

3. Inspect which profile rules fired:

   ```shell
   make transform
   make explain-transform
   ```

4. Build clean upstream artifacts:

   ```shell
   make build-upstream-artifacts
   ```

5. Generate a fresh tree and merge existing translations exactly:

   ```shell
   make export-fresh-translation-tree
   make merge-translation-tree
   ```

6. Inspect generated `outline.md`, `merge-report.json`, and representative
   `translation.md` files. The outline is regenerated from the current
   translation blocks, so its checked counts should match the filled, updated,
   and preserved translations reported by the merge step.
7. If the Markdown translation format changed, run an XLIFF export/import
   round trip and confirm it does not rewrite machine metadata unexpectedly.
8. Sync translations and render a demo PDF.
9. Confirm no translator-facing files contain raw Jinja or unnatural fragments.

## Synchronization After Parser Changes

Parser changes can invalidate old translation paths and hashes. The synchronization
policy is intentionally conservative:

- exact source hash and executable-placeholder matches may fill or update translations
- non-exact matches keep their target state and require version-specific review
- sentence-match suggestions should be treated as review hints, not automatic
  truth

When a parser change is broad, refresh public repository `sync/v*` branches
with clean scaffold artifacts and inspect what became untranslated before
asking translators to continue.

## Audits to Trust

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
