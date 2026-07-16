# QA Checklist

Use this before trusting tool-generated clean scaffold artifacts or parser
changes. Translation wording, glossary review, and manual import into any public
DSW instance belong in the public translated-template repository.

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
- full regression has `complete: true` in each
  `outputs/preview/**/random-project-coverage.json`
- the Actions run summary lists every planned version and does not report an
  unreadable or missing regression report

## Release Asset Checks

For each target version:

```shell
TOOL_GITHUB_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
CHECK_TAG=vX.Y.Z

gh release view "clean-scaffold-dsw-science-europe-$CHECK_TAG" \
  --repo "$TOOL_GITHUB_REPO"
```

Expected assets:

- clean workspace bundle
- scaffold package
- preview bundle or preview status file
- `SHA256SUMS`
- `release-notes.md`

Download and verify the checksum before using a clean scaffold artifact for
public repository refresh or cross-version synchronization.

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
- preview PDF exists for every supported runtime; `failed.json` is diagnostic,
  not an acceptable release result

For the public translated-template repository, review translated packages and PDFs
only for versions enabled by that repository's `version_policy`. A version can
be listed in `supported_versions` as a scaffold-only record without having an
active translation branch.

## Public Repository Integration

Before using artifacts in the public repository:

1. Download the clean scaffold release assets.
2. Verify `SHA256SUMS`.
3. Confirm the artifact version matches the upstream tag.
4. Import the package zip with `make render-package` and render the demo project;
   do not substitute a source-directory draft preview for this delivery check.
5. Confirm the tree passes structure audits.
6. Confirm the public repository documents translation QA and manual import.

Do not use local `outputs/` unless you intentionally built and reviewed
that exact local output.
