# Maintenance Runbook

Use this runbook for routine operation of a DSW document-template translation
repository.

## Daily Health Check

Check the operations workflow on the configured operations branch:

```shell
TRANSLATION_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
TRANSLATION_OPERATIONS_BRANCH=$(awk '/control_branch:/ { print $2; exit }' translation-config.yml)

gh run list \
  --repo "$TRANSLATION_REPO" \
  --workflow document_template_translation_sync.yml \
  --branch "$TRANSLATION_OPERATIONS_BRANCH" \
  --limit 5
```

Healthy outcomes:

- the workflow found no new clean scaffold artifacts;
- the workflow updated `translation-config.yml`;
- the workflow refreshed policy-enabled `sync/v*` branches;
- the workflow opened exact-source synchronization PRs for translation changes
  shared by active versions;
- the `translation-consistency-report` artifact records no unexplained gaps or
  wording drift across active/maintenance versions.

Operations waits for the version branch's `translation-sync` PR check and every
reported check to pass before performing a head-SHA-guarded merge. This does not
depend on repository-native auto-merge settings. A failed or timed-out check
leaves the synchronization PR open and does not change the target `sync/v*`
branch.

Synchronization PRs contain only exact-source `translation.md` updates and an
updated `outline.md` when progress changes. Review the merge report in the PR
body or Actions summary; reports are not committed to version branches. Merging
one of these automation PRs refreshes that version's package, preview, and
release assets without launching another reverse synchronization run.

The consistency artifact is read-only. An `exact-source` finding usually means
translation synchronization or review is still needed. A
`visible-source-only` finding is only a terminology prompt because executable
Jinja or HTML may differ between versions. Findings do not make CI fail, but a
missing or malformed configured translation tree does.

Check version-branch validation after translation PRs:

```shell
gh run list \
  --repo "$TRANSLATION_REPO" \
  --workflow document_template_translation_sync.yml \
  --branch sync/vX.Y.Z \
  --limit 5
```

## Manual Sync

Trigger operations sync after the tool repo publishes new clean scaffold assets:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_REPO" \
  --ref "$TRANSLATION_OPERATIONS_BRANCH"
```

Choose a synchronization source version when needed:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$TRANSLATION_REPO" \
  --ref "$TRANSLATION_OPERATIONS_BRANCH" \
  -f source_version=vX.Y.Z
```

Keep `tooling.repository` and `tooling.ref` in `translation-config.yml` as
ordinary one-line YAML scalars. The operations workflow uses those two values
to bootstrap the tool checkout, then delegates complete config validation to
the checked-out tool.

## Release Review

Before importing a translated template:

1. Confirm the version branch workflow passed.
2. Download the translated package, preview PDF, and `SHA256SUMS`.
3. Review glossary/i10n terminology and representative PDF pages.
4. Import the reviewed release package into the target DSW environment.

Do not treat tool-repo clean scaffold releases as translated outputs.
