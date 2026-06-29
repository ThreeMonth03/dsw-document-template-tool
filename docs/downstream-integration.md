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

The clean scaffold releases are inputs for downstream repositories. They are not
finished translations.

If upstream publishes a tag with an unsupported metamodel, scheduled/manual tool
repo CI may open a compatibility follow-up PR instead of producing a clean
scaffold release for that tag. Downstream repositories should wait for the
version-specific clean scaffold release before creating or refreshing a matching
translation branch.

## Clean Scaffold Releases

On successful scheduled runs, manual `workflow_dispatch` runs, and `master`
pushes, this repo publishes release assets named like:

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
TOOL_REPO=owner/document-template-tool
TRANSLATION_REPO=/path/to/translation-repo
TOOLING_ROOT=/path/to/document-template-tool
```

Download clean scaffold artifacts:

```shell
python scripts/ci/download_clean_scaffold_artifacts.py \
  --repo "$TOOL_REPO" \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds
```

When a downstream workflow is triggered by a specific tool-repo `workflow_run`,
prefer `--run-id` so it downloads artifacts from that exact run. Use the latest
successful lookup only for manual repair or exploratory maintenance.

```yaml
run: |
  python scripts/ci/download_clean_scaffold_artifacts.py \
    --repo "$TOOL_REPO" \
    --run-id "${{ github.event.workflow_run.id }}" \
    --output-dir /tmp/clean-scaffolds
```

Refresh version branches from downloaded artifacts:

```shell
python scripts/ci/sync_translation_version_branches.py \
  --repo "$TRANSLATION_REPO" \
  --tooling-root "$TOOLING_ROOT" \
  --clean-artifact-root /tmp/clean-scaffolds \
  --refresh-existing
```

Use `--dry-run` first when changing parser logic, supported versions, or branch
automation.

## Manual Downstream Sync

If the downstream translation repository uses the control-plane workflow from
this repo, operators can trigger a branch refresh without waiting for the daily
schedule:

```shell
TRANSLATION_REPO=owner/document-template-translation

gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_REPO" \
  --ref master
```

That run downloads the latest clean scaffold artifacts from the tool repo,
refreshes supported `translation/v*` branches, updates generated branch
workflows, and may create migration PRs.

To choose the source branch used for migration fan-out, pass `source_version`:

```shell
TRANSLATION_REPO=owner/document-template-translation

gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_REPO" \
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
