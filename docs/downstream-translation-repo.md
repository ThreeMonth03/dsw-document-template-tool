# Downstream Translation Repo

This document explains how `ThreeMonth03/DSW-document-template-translation`
uses the tooling repo.

## Branch Layout

- `master`: control plane only. It should contain configuration, documentation,
  shared fixtures, and workflows, but no version-specific document template
  workspace.
- `translation/v*`: one branch per upstream template version. Translators edit
  `workspace/document-templates/translation/.../tree/**/translation.md` here.
- `archive/*`: historical safety snapshots.

Supported branches currently include:

- `translation/v1.29.1`
- `translation/v1.30.0`
- `translation/v1.30.1`

## Configuration

The control file is:

```text
translation-config.yml
```

It declares:

- upstream repository and supported versions
- source and target language IDs
- translated template identity
- branch naming
- tooling repository and ref
- migration policy

Adding a new upstream tag to the translation workflow requires updating this
config and creating or refreshing the matching `translation/v*` branch.

The tool repo can discover and package clean scaffold artifacts for new upstream
tags, but it does not by itself make the downstream translation repo complete.
For each supported version, verify all three layers:

- clean scaffold release exists in the tool repo
- `translation/v*` branch exists and has migrated or empty review blocks
- translated package/PDF release exists in the translation repo

## Clean Scaffold Inputs

The translation repo should consume clean scaffold artifacts from the tool repo,
not copy random local workspaces by hand. Use:

```shell
python scripts/ci/download_clean_scaffold_artifacts.py \
  --repo ThreeMonth03/DSW-document-template-tool \
  --workflow headless_render_regression.yml \
  --output-dir /tmp/clean-scaffolds
```

Then refresh version branches with:

```shell
python scripts/ci/sync_translation_version_branches.py \
  --repo /path/to/DSW-document-template-translation \
  --tooling-root /path/to/DSW-document-template-tool \
  --clean-artifact-root /tmp/clean-scaffolds \
  --refresh-existing
```

Use `--dry-run` first when changing parser logic or supported versions.

## Migration Policy

Migration is exact-only by default:

- same source hash and executable placeholders: copy translation
- changed source, placeholder, Jinja, or HTML structure: leave translation empty
  and mark it for review

This avoids silently applying stale wording to a changed upstream sentence.

## Release Assets

Each version branch refreshes its own release assets after a successful push CI
run. Confirm with:

```shell
gh release view science-europe-zh-hant-v1.30.1 \
  --repo ThreeMonth03/DSW-document-template-translation
```

The release is a review/download bucket. depositar import remains manual.

## Workflow Synchronization

The file under `examples/github-actions/` in this repo is only a template. When
we fix a workflow behavior, apply it to every supported `translation/v*` branch
that still needs it.

Checklist after workflow changes:

1. Push each affected version branch.
2. Confirm CI passes.
3. Confirm `document-template-package-*` Actions artifact exists.
4. Confirm `document-template-preview-*` Actions artifact exists.
5. Confirm the versioned GitHub Release contains zip, PDF, JSON, and
   `SHA256SUMS`.

## New Upstream Version Checklist

When a new upstream tag appears:

1. Wait for the tool repo clean scaffold release or run the tool workflow
   manually.
2. Update `translation-config.yml` on the translation repo control branch.
3. Create or refresh the corresponding `translation/v*` branch from the clean
   scaffold artifact.
4. Run exact-only migration from the closest reviewed version.
5. Leave non-exact units empty for review rather than copying stale text.
6. Push the version branch and confirm the versioned release assets refresh.

This keeps branch history explicit and avoids silently publishing a template
version that only exists as an untranslated scaffold.
