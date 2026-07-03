# QA Checklist

Use this before trusting tool-generated clean scaffold artifacts or parser
changes. Translation wording, glossary review, and manual import into any public
DSW instance belong in the downstream translation repository.

## Structural Checks

Run or confirm CI ran:

```shell
make check
```

For a generated translation tree or synced output:

```shell
make audit-translation-tree
make sync-translation-tree
make audit-translated-template
```

Confirm:

- no raw Jinja leaked into translator-editable text
- placeholders are preserved
- translated output keeps executable Jinja and HTML structure
- package generation succeeds

## Release Asset Checks

For each target version:

```shell
TOOL_GITHUB_REPO=owner/document-template-tool

gh release view clean-scaffold-dsw-science-europe-vX.Y.Z \
  --repo "$TOOL_GITHUB_REPO"
```

Expected assets:

- clean workspace bundle
- scaffold package
- preview bundle or preview status file
- `SHA256SUMS`
- `release-notes.md`

Download and verify the checksum before using a clean scaffold artifact for
downstream migration.

## PDF Review

Open the demo PDF and inspect:

- cover page title, project name, and metadata
- table/list rendering
- representative conditional sections
- punctuation near optional text
- font readability and heading/body hierarchy

Do not make layout changes only because a generated scaffold preview looks
visually different from another language. Change layout only when the output
loses structure or readability.

## Version Coverage

For all known scaffold versions:

- tool repo clean scaffold release exists
- clean scaffold artifact includes compact, expanded, and translation trees
- scaffold package exists
- preview PDF exists or a clear `failed.json` / `skipped.json` explains why

For downstream translation repositories, review translated packages and PDFs
only for versions enabled by that repository's `version_policy`. A version can
be listed in `supported_versions` as a scaffold-only record without having an
active translation branch.

## Downstream Handoff

Before handing artifacts to a translation repository:

1. Download the clean scaffold release assets.
2. Verify `SHA256SUMS`.
3. Confirm the artifact version matches the upstream tag.
4. Confirm the tree passes structure audits.
5. Confirm the downstream repository documents translation QA and manual import.

Do not hand off local `outputs/` unless you intentionally built and reviewed
that exact local output.
