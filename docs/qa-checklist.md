# QA Checklist

Use this before asking someone to import a translated package into DSW/depositar.

## Structural Checks

Run or confirm CI ran:

```shell
make format-check
make lint
make test
```

For a translated template:

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
gh release view science-europe-zh-hant-vX.Y.Z \
  --repo ThreeMonth03/DSW-document-template-translation
```

Expected assets:

- `dsw-science-europe-zh-hant-vX.Y.Z.zip`
- `test-project-vX.Y.Z.pdf`
- `test-project-vX.Y.Z.pdf.json`
- `SHA256SUMS`
- `release-notes.md`

Download and verify the checksum before manual import.

## PDF Review

Open the demo PDF and inspect:

- cover page title, project name, and metadata
- table/list rendering
- representative conditional sections
- punctuation near translated optional text
- glossary terms and i10n wording
- obvious fallback English text
- font readability and heading/body hierarchy

Do not make layout changes only because the Chinese PDF has a different visual
texture from the English PDF. Change layout only when the output loses structure
or readability.

## Version Coverage

For all supported versions:

- tool repo clean scaffold release exists
- translation branch exists
- translation branch CI is green
- translation release asset exists
- demo PDF exists or a clear `failed.json` / `skipped.json` explains why

## Manual Import

Before importing into DSW/depositar:

1. Download the versioned zip from the translation repo release.
2. Verify `SHA256SUMS`.
3. Import into a test DSW environment when possible.
4. Render the demo project or a representative real project.
5. Only then import into the intended target environment.

Do not import from local `outputs/` unless you intentionally built and reviewed
that local output.
