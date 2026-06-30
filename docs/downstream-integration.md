# Downstream Integration

This document explains the boundary between this tooling repository and a
translation control repository.

## What This Repo Provides

The tool repo owns reusable infrastructure:

- parser and template transform logic
- translation tree export, merge, sync, and audits
- clean upstream scaffold artifacts for supported template tags
- demo KM/project fixtures used by CI previews
- helper scripts under `scripts/ci/`
- copy-paste workflow templates under `examples/`

The clean scaffold outputs are inputs for downstream repositories. They are not
finished translations.

This repo exposes those outputs in two places:

- GitHub Actions artifacts from `headless_render_regression.yml`, which the
  translation control workflow downloads during automated sync.
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

- version branches such as `translation/v1.30.1`
- translator-facing `translation.md` edits
- glossary and i10n review
- translated package/PDF release assets
- manual import or publication policy

Keep those operational details in the translation repository documentation. This
repo should only document the artifact contract and helper commands.

## Helper Scripts Used By Downstream

Set repository paths once:

```shell
TOOL_GITHUB_REPO=owner/document-template-tool
TRANSLATION_GITHUB_REPO=owner/document-template-translation
TOOL_REPO_DIR=/path/to/document-template-tool
TRANSLATION_REPO_DIR=/path/to/document-template-translation
```

Download clean scaffold artifacts:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/download_clean_scaffold_artifacts.py" \
  --repo "$TOOL_GITHUB_REPO" \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds
```

Downstream repositories normally cannot receive a cross-repository
`workflow_run` event from this tool repository. The operations workflow
therefore downloads the latest successful tool-repo run by workflow name. If an
operator passes an exact tool run id manually, prefer `--run-id` so the
downloaded artifacts are tied to that exact run:

```shell
TOOLING_RUN_ID=123456789

"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/download_clean_scaffold_artifacts.py" \
  --repo "$TOOL_GITHUB_REPO" \
  --run-id "$TOOLING_RUN_ID" \
  --output-dir /tmp/clean-scaffolds
```

Refresh version branches from downloaded artifacts:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/scripts/ci/sync_translation_version_branches.py" \
  --repo "$TRANSLATION_REPO_DIR" \
  --tooling-root "$TOOL_REPO_DIR" \
  --clean-artifact-root /tmp/clean-scaffolds \
  --refresh-existing
```

Use `--dry-run` first when changing parser logic, supported versions, or branch
automation.

## Manual Downstream Sync

If the downstream translation repository uses the operations workflow from
this repo, operators can trigger a branch refresh without waiting for the daily
schedule:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_GITHUB_REPO" \
  --ref master
```

That run downloads the latest clean scaffold artifacts from the tool repo,
refreshes supported `translation/v*` branches, updates generated branch
workflows, and may create migration PRs.

To choose the source branch used for migration fan-out, pass `source_version`:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_GITHUB_REPO" \
  --ref master \
  -f source_version=v1.30.1
```

Use this after tool-repo workflow template changes, parser changes, fixture
changes, or clean scaffold release refreshes. It is still downstream-owned:
review the translation repo Actions run, migration PRs, and release assets
there.

## Workflow Template

`examples/github-actions/document_template_translation_sync.yml` is a template
for downstream repositories. Updating it here does not update existing
downstream version branches. Apply important workflow fixes to each supported
translation branch in the downstream repo.
