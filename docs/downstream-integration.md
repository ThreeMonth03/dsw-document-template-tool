# Downstream Integration

This document explains the boundary between this tooling repository and a
downstream translation repository.

## What This Repo Provides

The tool repo owns reusable infrastructure:

- parser and template transform logic
- translation tree export, merge, sync, and audits
- clean upstream scaffold artifacts for supported template tags
- demo project fixtures and matching Knowledge Model bundles used by CI previews
- helper scripts under
  [`scripts/ci/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/scripts/ci)
- copy-paste workflow templates under
  [`examples/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples)

The clean scaffold outputs are inputs for downstream repositories. They are not
finished translations.

This repo exposes those outputs in two places:

- GitHub Actions artifacts from
  [`.github/workflows/headless_render_regression.yml`](../.github/workflows/headless_render_regression.yml),
  which the downstream translation workflow downloads during automated sync.
- GitHub Release assets named `clean-scaffold-dsw-science-europe-vX.Y.Z`, which
  are stable human-facing download buckets for review and handoff.

If upstream publishes a tag with an unsupported metamodel, scheduled/manual tool
repo CI may open a compatibility probe PR instead of producing clean scaffold
outputs for that tag. Downstream repositories should wait for a successful
tool-repo run, and preferably the matching version-specific release, before
creating or refreshing a matching translation branch.

## Clean Scaffold Outputs

On successful scheduled runs, manual `workflow_dispatch` runs, and `master`
pushes, this repo uploads Actions artifacts and publishes release assets named
like:

```text
clean-scaffold-dsw-science-europe-v1.30.1
```

Typical assets include:

- clean compact/expanded/translation workspace bundle
- scaffold template package
- demo preview bundle
- `SHA256SUMS`
- `release-notes.md`

These releases are download buckets. Assets may be overwritten by later CI runs
for the same upstream tag; use release notes, checksums, and workflow metadata
for provenance.

## What the Translation Repo Owns

A downstream translation repository owns:

- a configured operations branch containing `translation-config.yml`, docs,
  fixtures, and repository workflows
- version branches such as `translation/v1.30.1`
- public handoff branches using the configured publish prefix, such as
  `sync/v1.30.1`, when the same repository also stores clean translated
  template source
- translator-facing `translation.md` edits
- the user-facing public README copied into generated DSW template packages
- glossary and i10n review
- translated package/PDF release assets
- manual import or publication policy

Keep those operational details in the translation repository documentation. This
repo should only document the artifact contract and helper commands.
If the downstream repo also has a `master` branch, this tooling does not require
automation to write to it.

## Helper Scripts Used By Downstream

Set repository paths once:

```shell
TOOL_GITHUB_REPO=owner/document-template-tool
TRANSLATION_GITHUB_REPO=owner/document-template-translation
TRANSLATION_OPERATIONS_BRANCH=master
TOOL_REPO_DIR=/path/to/document-template-tool
TRANSLATION_REPO_DIR=/path/to/document-template-translation
```

Download clean scaffold artifacts:

```shell
make download-clean-scaffold-artifacts \
  TOOL_GITHUB_REPO="$TOOL_GITHUB_REPO" \
  CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR=/tmp/clean-scaffolds
```

Downstream repositories normally cannot receive a cross-repository
`workflow_run` event from this tool repository. The operations workflow
therefore downloads the latest successful tool-repo run by workflow name. If an
operator passes an exact tool run id manually, prefer `--run-id` so the
downloaded artifacts are tied to that exact run:

```shell
TOOLING_RUN_ID=123456789

make download-clean-scaffold-artifacts \
  TOOL_GITHUB_REPO="$TOOL_GITHUB_REPO" \
  CLEAN_SCAFFOLD_ARTIFACT_RUN_ID="$TOOLING_RUN_ID" \
  CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR=/tmp/clean-scaffolds
```

Refresh version branches from downloaded artifacts:

```shell
make sync-translation-version-branches \
  TRANSLATION_REPO="$TRANSLATION_REPO_DIR" \
  TRANSLATION_CLEAN_ARTIFACT_ROOT=/tmp/clean-scaffolds \
  TRANSLATION_SYNC_REFRESH_EXISTING=true
```

Check cross-version migration status after the refresh:

```shell
make check-translation-migrations \
  TRANSLATION_REPO="$TRANSLATION_REPO_DIR" \
  TRANSLATION_CLEAN_ARTIFACT_ROOT=/tmp/clean-scaffolds
```

Use `--dry-run` first when changing parser logic, supported versions, or branch
automation. Scheduled workflows should keep the default `--policy-mode auto`;
operator-triggered maintenance refreshes can pass `--policy-mode manual` if the
downstream repository's `version_policy` allows it.

By default, version-branch sync does not create, update, or delete files under
`.github/workflows/`. This keeps routine scaffold refreshes usable with the
standard GitHub Actions token, which cannot modify workflow files. When you
intentionally need to regenerate version-branch workflow files, rerun the helper
with `--sync-workflows` and a token that has GitHub Actions workflow scope.

`template.supported_versions` is the downstream repository's known upstream
version ledger. It may contain versions that have clean scaffold artifacts but
are not actively translated. Branch creation and content refresh are controlled
by `version_policy`: only versions whose effective `refresh` value is `auto`
for scheduled runs, or `auto`/`manual` for operator-triggered runs, get
`translation/v*` workspaces. If `version_policy` is omitted, the tool treats
newly discovered versions as scaffold-only records and does not create
translation branches.

The branch sync workflow reads `public_readme.path` from the downstream
`translation-config.yml`. The default is:

```text
workspace/document-templates/public-readme/README.md
```

When that file exists on a version branch, translated package generation copies
it to the output template's `README.md`. If it does not exist, the tool writes a
short fallback README.

Configured public README files may use these lightweight placeholders:

- `{template_full_id}`
- `{template_id}`
- `{template_organization_id}`
- `{template_version}`

The placeholders are replaced from the generated `template.json` before the DSW
package is created. Use `{template_version}` to link to the corresponding
upstream tag, for example:

```text
https://github.com/ds-wizard/science-europe-template/blob/v{template_version}/README.md
```

Public handoff branches should stay close to the upstream template repository
shape. The publish helper copies generated template source while filtering
tool-internal metadata such as `.transform/` and `UPSTREAM-README.md`.

## Manual Downstream Sync

If the downstream translation repository uses the operations workflow from
this repo, operators can trigger a branch refresh without waiting for the daily
schedule:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_GITHUB_REPO" \
  --ref "$TRANSLATION_OPERATIONS_BRANCH"
```

That run downloads the latest clean scaffold artifacts from the tool repo and
updates `translation-config.yml` on the operations branch. It creates or
refreshes only policy-enabled `translation/v*` branches and may create
exact-only migration PRs. Routine version-branch sync preserves existing
workflow files; use `--sync-workflows` only for explicit workflow maintenance.
Version-branch sync treats `translation.md` as canonical. Optional XLIFF
exchange is available as a helper command, but it is not part of the default
branch automation.

If no migration PR appears, use `make check-translation-migrations` against the
same clean scaffold artifacts to distinguish "nothing to migrate" from "the
workflow did not run the migration step."

To choose the source branch used for migration fan-out, pass `source_version`:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_GITHUB_REPO" \
  --ref "$TRANSLATION_OPERATIONS_BRANCH" \
  -f source_version=v1.30.1
```

Use this after tool-repo workflow template changes, parser changes, fixture
changes, or clean scaffold release refreshes. It is still downstream-owned:
review the translation repo Actions run, migration PRs, and release assets
there.

## Workflow Template

[`examples/github-actions/document_template_translation_sync.yml`](../examples/github-actions/document_template_translation_sync.yml)
is a template for downstream repositories. Updating it here does not update
existing downstream version branches. Routine branch refreshes preserve workflow
files to avoid requiring elevated token scopes. Apply important workflow fixes
in the downstream repo by running `make sync-translation-version-branches` with
`TRANSLATION_SYNC_WORKFLOWS=true`, or by making an explicit workflow-only
maintenance commit there.

The template is intended for version-specific `translation/v*` branches. It is
triggered by pull requests, pushes, and manual dispatch. Daily scheduled
maintenance belongs in the downstream operations workflow on the default branch;
do not rely on `schedule` triggers in generated version-branch workflows.
