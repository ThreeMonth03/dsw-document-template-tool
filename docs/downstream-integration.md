# Public Template Repository Integration

This document explains the boundary between this tooling repository and a
public translated-template repository such as
`depositar/science-europe-template-zh_Hant`.

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
- copy-ready public-repository documentation templates under
  [`examples/translation-repository/`](https://github.com/ThreeMonth03/dsw-document-template-tool/tree/master/examples/translation-repository)

The clean scaffold outputs are inputs for the public translated-template
repository. They are not finished translations.

This repo exposes those outputs in two places:

- GitHub Actions artifacts from
  [`.github/workflows/headless_render_regression.yml`](../.github/workflows/headless_render_regression.yml),
  which the public repository workflow downloads during automated sync.
- GitHub Release assets named `clean-scaffold-dsw-science-europe-vX.Y.Z`, which
  are stable human-facing download buckets for review and integration.

If upstream publishes a tag with an unsupported metamodel, scheduled/manual tool
repo CI may open a compatibility probe PR instead of producing clean scaffold
outputs for that tag. The public repository should wait for a successful
tool-repo run, and preferably the matching version-specific release, before
recording the new version or refreshing a matching `sync/v*` branch.

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

## What the Public Repository Owns

The public translated-template repository owns:

- a configured operations branch containing `translation-config.yml`, docs,
  fixtures, and repository workflows
- version branches such as `sync/v1.30.1`
- translator-facing `translation.md` edits on `sync/v*` branches
- the user-facing public README copied into generated DSW template packages
- glossary and i10n review
- translated package/PDF release assets and full package-regression evidence
- manual import or publication policy

Keep those operational details in the public repository documentation. This
repo documents the artifact contract and helper commands.
The tool repo does not require automation to write to the public repository's
`master` branch unless that repository chooses to run operations from `master`.
The configured `branches.control_branch` does not have to be the repository's
default branch. Dispatch operations explicitly to that branch and keep merge
cleanup hooks on each PR target branch. This works with `main` as the default
branch and `operations` as the control branch without scheduled workflows.

## Integrated Public Repository Layout

The current project keeps translation work and public release assets in the
same depositar repository, while keeping responsibilities branch-separated:

| Branch or asset | Purpose |
| --- | --- |
| operations branch, usually `master` | Repository-level config, workflows, and docs. |
| `sync/v*` | Translator-facing workspaces and review PRs. |
| release assets | Default delivery path: package zip, preview PDF, checksums, and notes. |

This layout is an organizational boundary, not a privacy boundary. If the
public repository is public, draft translation branches, PRs, logs, and
artifacts may be public too. Keep `sync/v*` branches in a private repo or
private fork if draft wording must stay private.

Use [Public Repository Templates](translation-repository-templates.md) for
copy-ready README/runbook files. The copies in the public repository become
repository-owned; updating this tool repo does not rewrite them automatically.

## Helper Scripts Used By The Public Repository

Set repository paths once:

```shell
TOOL_GITHUB_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
PUBLIC_TEMPLATE_GITHUB_REPO=owner/science-europe-template-zh_Hant
TRANSLATION_OPERATIONS_BRANCH=master
TOOL_REPO_DIR=/path/to/document-template-tool
PUBLIC_TEMPLATE_REPO_DIR=/path/to/science-europe-template-zh_Hant
```

Download clean scaffold artifacts:

```shell
TOOLING_RUN_ID=123456789

make download-clean-scaffold-artifacts \
  TOOL_GITHUB_REPO="$TOOL_GITHUB_REPO" \
  CLEAN_SCAFFOLD_ARTIFACT_RUN_ID="$TOOLING_RUN_ID" \
  CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR=/tmp/clean-scaffolds
```

The public repository normally cannot receive a cross-repository
`workflow_run` event from this tool repository. Pass the exact run id from a
trusted `master` push, scheduled run, or operator-dispatched run into the
operations workflow instead. Automated sync must use `--run-id` (exposed by the
Make target as `CLEAN_SCAFFOLD_ARTIFACT_RUN_ID`) so downloaded artifacts are
tied to a reviewed producer run. Do not resolve the latest successful run by
workflow name in automation: pull requests also run the producer workflow and
upload artifacts.

Lookup by workflow name remains available only for manual repair or exploratory
maintenance where an operator verifies the selected run's event, branch, commit,
and actor before any output is used:

```shell
make download-clean-scaffold-artifacts \
  TOOL_GITHUB_REPO="$TOOL_GITHUB_REPO" \
  CLEAN_SCAFFOLD_ARTIFACT_OUTPUT_DIR=/tmp/clean-scaffolds
```

Refresh version branches from downloaded artifacts:

```shell
make sync-translation-version-branches \
  TRANSLATION_REPO="$PUBLIC_TEMPLATE_REPO_DIR" \
  TRANSLATION_CLEAN_ARTIFACT_ROOT=/tmp/clean-scaffolds \
  TRANSLATION_SYNC_REFRESH_EXISTING=true
```

Check cross-version migration status after the refresh:

```shell
make check-translation-migrations \
  TRANSLATION_REPO="$PUBLIC_TEMPLATE_REPO_DIR" \
  TRANSLATION_CLEAN_ARTIFACT_ROOT=/tmp/clean-scaffolds
```

Generate the read-only wording consistency report from active/maintenance
`sync/v*` branches:

```shell
make report-translation-consistency \
  TRANSLATION_REPO="$PUBLIC_TEMPLATE_REPO_DIR" \
  TRANSLATION_CONSISTENCY_FETCH=true
```

The complete JSON and Markdown reports are written under
`outputs/translation-consistency/`. Differences are review signals, not an
alternative migration path: only exact-source synchronization may write to a
target branch.

Check that public repository docs still cover the required operations topics:

```shell
make check-translation-repository-docs \
  TRANSLATION_DOCS_REPO="$PUBLIC_TEMPLATE_REPO_DIR"
```

Use `--dry-run` first when changing parser logic, supported versions, or branch
automation. Scheduled workflows should keep the default `--policy-mode auto`;
operator-triggered maintenance refreshes can pass `--policy-mode manual` if the
public repository's `version_policy` allows it.

By default, version-branch sync does not create, update, or delete files under
`.github/workflows/`. This keeps routine scaffold refreshes usable with the
standard GitHub Actions token, which cannot modify workflow files. When you
intentionally need to regenerate version-branch workflow files, rerun the helper
with `--sync-workflows` and a token that has GitHub Actions workflow scope.

`template.supported_versions` is the public repository's known upstream
version ledger. It may contain versions that have clean scaffold artifacts but
are not actively translated. Branch creation and content refresh are controlled
by `version_policy`: only versions whose effective `refresh` value is `artifact`
for scheduled runs, or `artifact`/`manual` for operator-triggered runs, get
`sync/v*` workspaces. If `version_policy` is omitted, the tool treats
newly discovered versions as scaffold-only records and does not create
translation branches.

The branch sync workflow reads `public_readme.path` from the public repository
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

## Manual Public Repository Sync

The tool repo provides helper scripts and a version-branch workflow template,
but the default-branch operations workflow belongs to the public repository. If
that repository has an operations workflow that calls
`make download-clean-scaffold-artifacts` and
`make sync-translation-version-branches`, operators can trigger a branch refresh
without waiting for its daily schedule:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$PUBLIC_TEMPLATE_GITHUB_REPO" \
  --ref "$TRANSLATION_OPERATIONS_BRANCH"
```

The public-repository workflow must be configured with the exact trusted tool
run id; do not let a write-enabled sync select the latest successful run by
workflow name. It downloads clean scaffold artifacts from that pinned run and
updates `translation-config.yml` on the public repository operations branch. It
creates or refreshes only
policy-enabled `sync/v*` branches and may create exact-source synchronization
PRs. These PRs fill blank units and update existing translations only for
structurally identical source units. Routine version-branch sync preserves existing workflow files; use
`--sync-workflows` only for explicit workflow maintenance. Version-branch sync
treats `translation.md` as canonical. Optional XLIFF exchange is available as a
helper command, but it is not part of the default branch automation.

Synchronization PRs merge only after their version-branch `translation-sync`
check and every other reported check pass. The operations job waits for those
checks and then performs a head-SHA-guarded merge; it does not depend on
repository-native auto-merge settings. Failed or timed-out checks leave the PR
open without changing the target branch.

The version-branch check imports the generated package ZIP twice for distinct
purposes: one representative demo render produces the review PDF, while the
translated-package regression renders the complete selected fixture set and
requires complete branch coverage. Release assets include the regression report
and coverage JSON so package validation remains traceable after Actions
artifacts expire.

The PR diff is deliberately narrow: matching `translation.md` files and an
updated `outline.md` are allowed, while template structure, manifests, README
files, packages, and diagnostic reports are rejected. The detailed merge report
is available in the PR body and Actions summary. Merging an automation-generated
synchronization PR validates and republishes the target version without starting
a redundant reverse fan-out.

If no synchronization PR appears, use `make check-translation-migrations`
against the same clean scaffold artifacts to distinguish "all exact-source
translations are aligned" from "the workflow did not run the synchronization
step."

If public repository docs were copied or rewritten, run
`make check-translation-repository-docs` before handing the repository back to
operators.

To choose the source branch used for migration fan-out, pass `source_version`:

```shell
gh workflow run document_template_translation_sync.yml \
  --repo "$PUBLIC_TEMPLATE_GITHUB_REPO" \
  --ref "$TRANSLATION_OPERATIONS_BRANCH" \
  -f source_version=v1.30.1
```

Use this after tool-repo workflow template changes, parser changes, fixture
changes, or clean scaffold release refreshes. It is still public-repository-owned:
review the public repository Actions run, synchronization PRs, and release assets
there.

## Workflow Template

[`examples/github-actions/document_template_translation_sync.yml`](../examples/github-actions/document_template_translation_sync.yml)
is a template for public repository version branches. It is not the public
repository
default-branch operations workflow. Updating it here does not update existing
public repository version branches. Routine branch refreshes preserve workflow files
to avoid requiring elevated token scopes. Apply important workflow fixes in the
public repository by running `make sync-translation-version-branches` with
`TRANSLATION_SYNC_WORKFLOWS=true`, or by making an explicit workflow-only
maintenance commit there.

Actions artifacts expire after 7 days, or 14 days for pull-request runs. The
cleanup workflow removes allowlisted artifacts earlier once their PRs have merged
and the runs have completed. Download review evidence before merging or before it
expires. GitHub Release assets and non-PR runs are unaffected by PR cleanup.
Set the operations workflow's consistency-report retention to 7 days too.

**Clean merged PR artifacts** runs only when a same-repository PR merges. It
checks PR ownership through GitHub metadata and skips unknown, running, or
unmerged work. Each merge removes up to 100 eligible artifacts, including older
merged PRs. Later merges continue a backlog. Artifacts skipped because CI is
still running or the PR is from a fork wait for a later eligible merge or their
retention expiry. Results stay in job logs and summaries.

The template is intended for version-specific `sync/v*` branches. It is
triggered by pull requests, pushes, and manual dispatch on those branches. The
generated `artifact_cleanup.yml` is a separate merge-only hook, so closing a PR
does not restart translation builds. Synchronize both workflow files to existing
version branches; updating the tooling template alone does not install the hook.
Do not rely on default-branch-only events such as `schedule` or `workflow_run`
for a repository whose operations branch is not its default branch.
