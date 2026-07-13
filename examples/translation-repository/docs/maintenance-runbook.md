# Maintenance Runbook

Use this runbook for routine operation of a DSW document-template translation
repository.

## Daily Health Check

Check the operations workflow on the configured operations branch:

```shell
gh run list --workflow document_template_translation_sync.yml --branch master --limit 5
```

Healthy outcomes:

- the workflow found no new clean scaffold artifacts;
- the workflow updated `translation-config.yml`;
- the workflow refreshed policy-enabled `sync/v*` branches;
- the workflow opened exact-only migration PRs for safe carry-over changes.

Check version-branch validation after translation PRs:

```shell
gh run list --workflow document_template_translation_sync.yml --branch sync/v1.30.1 --limit 5
```

## Manual Sync

Trigger operations sync after the tool repo publishes new clean scaffold assets:

```shell
gh workflow run document_template_translation_sync.yml --ref master
```

Choose a migration source version when needed:

```shell
gh workflow run document_template_translation_sync.yml \
  --ref master \
  -f source_version=v1.30.1
```

## Release Review

Before importing a translated template:

1. Confirm the version branch workflow passed.
2. Download the translated package, preview PDF, and `SHA256SUMS`.
3. Review glossary/i10n terminology and representative PDF pages.
4. Import the reviewed release package into the target DSW environment.

Do not treat tool-repo clean scaffold releases as translated outputs.
