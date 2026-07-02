# Translation Workflow

This document explains how the tooling turns an upstream DSW document template
into a translator-facing tree, then syncs that tree back into a packageable
template. Translator day-to-day instructions belong in the downstream
translation repository.

## Workspace Shapes

The translation pipeline has three workspace shapes:

- `compact`: the upstream DSW document template source.
- `expanded`: the same template with sentence-preserving marker comments around
  translatable units.
- `translation`: one Markdown file per translation unit, optimized for human
  review and editing.

The reversible path is:

```text
compact -> expanded -> translation -> translated expanded -> package
```

The standard commands are:

```shell
make transform
make export-translation-tree
make sync-translation-tree
```

When the upstream template or parser changes, regenerate a fresh tree and merge
existing translations conservatively:

```shell
make export-fresh-translation-tree
make merge-translation-tree
```

## Expanded Workspace

`make transform` generates an expanded template workspace from a compact DSW
template. The original `.j2` files stay in place, but translatable regions are
wrapped with generated comments such as `__tr_block_####`.

The markers are comments, not `{% set %}` captures. They preserve larger units
such as headings, paragraphs, list items, and branch-complete sentence groups
without changing Jinja scope.

The generated expanded workspace includes:

- original template files under their normal paths
- generated translation markers
- a generated `README.md`
- the upstream README preserved as `UPSTREAM-README.md` when present
- `.transform/manifest.json` for machine checks

The generated `README.md` in the expanded workspace is internal. During
translated output sync, the tool copies the downstream translation repo's
configured public README into the package when that file exists. If it is
missing, the tool writes a short fallback README so the DSW package still has a
displayable description. The public publish handoff intentionally excludes
internal-only files such as `.transform/` and `UPSTREAM-README.md`; public
README text should link to the upstream GitHub README instead of copying it into
the public repository.

## Translator-Facing Tree

`make export-translation-tree` writes one `translation.md` file per translation
unit. Each file shows the source sentence first and the editable target block
second. Machine metadata is kept in a collapsed details section so translators
can inspect it when needed without having it dominate the page.

Translator-facing tree rules enforced by this tooling:

- every editable file has a stable source block and target translation block
- every placeholder that appears in the source sentence, such as `{name}`, must
  remain present after translation
- Placeholders may be reordered for grammar.
- raw `{{ ... }}` or `{% ... %}` Jinja is not allowed in translation text
- broken or deleted translation block skeletons can be regenerated

The generated `outline.md` gives reviewers a compact progress view of all
translation units. It is committed, but it is not edited by hand: export, merge,
and CI refreshes recalculate it from the current `translation.md` blocks so a
filled translation block automatically becomes a checked item.

## Weblate Exchange

The canonical translation source is still the Markdown translation tree.
Weblate should be treated as an editing interface, not as the source of truth.

Use XLIFF as the exchange boundary:

```shell
make export-weblate-xliff
make import-weblate-xliff
```

`make export-weblate-xliff` reads the current translation tree and writes a
standard XLIFF 1.2 file. Weblate can edit that file without understanding the
custom `translation.md` format.

`make import-weblate-xliff` writes XLIFF targets back into the editable
translation blocks. Import checks that every XLIFF unit still belongs to the
current tree and that the source hash matches. Placeholder, Jinja, and HTML
safety checks remain the responsibility of `make audit-translation-tree` and
`make sync-translation-tree`, so the validation rules stay centralized.

Do not point Weblate at generated compact, expanded, translated output, or
public publish branches. It should only edit the downstream translation
repository's XLIFF exchange file.

For small-team automation, Weblate should push that XLIFF to a review branch
such as `weblate/v1.30.1`. The generated promotion workflow then checks out the
matching `translation/v1.30.1` branch, copies only the XLIFF from the Weblate
branch, imports it into `translation.md`, audits the tree, validates translated
output structure, and pushes the safe result to `translation/v1.30.1`.

Version-branch CI uses the same boundary automatically. Before regenerating the
tree it imports the branch XLIFF file into `translation.md`; after refresh and
merge it exports a new XLIFF file. That keeps Weblate edits and Markdown
translation review in sync without making Weblate understand the internal tree
layout.

## Sync and Audit

`make sync-translation-tree` applies translator edits into a generated translated
expanded workspace and packages it. During sync, the tooling checks that
placeholders, Jinja structure, HTML wiring, links, assets, and static files stay
structurally safe.

Blank translation blocks intentionally fall back to the English source text.
That allows scaffold artifacts to be generated before translation is complete,
but such artifacts are not finished translations.

Useful checks:

```shell
make audit-translation-tree
make sync-translation-tree
make audit-translated-template
```

## Version Migration Helpers

Downstream translation repos commonly use one branch per upstream template
version. This repo provides helpers for that model, but the branch policy itself
belongs downstream.

Cross-version migration is exact-only by default. A translation is copied only
when the source hash and executable placeholders match. If the source sentence,
Jinja shape, or HTML structure changed, the target translation block stays empty
and needs human review.

The helper scripts live under `scripts/ci/`:

- `sync_translation_version_branches.py`
- `create_translation_migration_prs.py`
- `validate_translation_config.py`
- `download_clean_scaffold_artifacts.py`
- `resolve_migration_source.py`

See [Downstream Integration](downstream-integration.md) for the artifact
contract between this repo and downstream translation repositories.
