# Branch Policy

This repository may combine translation work and public handoff in one GitHub
repository, but the responsibilities must stay separated by branch.

## Branch Layout

| Branch or asset | Purpose |
| --- | --- |
| `master` or the configured operations branch | Repository-level docs, `translation-config.yml`, and workflows. |
| `sync/v*` | Translator-facing Markdown workspaces and review PRs. |
| Release assets | Default delivery path: package zip, preview PDF, checksums, and release notes. |
| Optional `publish/v*` or configured handoff branch prefix | Clean translated source only when branch-based handoff is enabled. |

Do not publish translator-facing workspaces as final template source. Use the
release asset for reviewed handoff unless branch-based source handoff has been
explicitly enabled.

## Public Visibility

If this repository is public, translation branches and pull requests are public
too. That means draft translation wording, CI logs, preview artifacts, and
review discussions may be visible.

If draft translation work must stay private, keep `sync/v*` branches in a
private repository or private fork and publish only reviewed release assets or
explicitly enabled source handoff branches.

## Version Policy

`translation-config.yml` controls which upstream versions are known and which
versions automation may refresh. A version can be scaffold-only without an
active translation branch.

Use `version_policy` to decide whether a version is active, maintenance-only,
or archived. Do not assume every upstream template tag needs an active
translation branch.

## Common Policy Snippets

Scaffold exists, but translation has not started:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: available
      refresh: false
      migrate_into: false
      publish_release: false
      reason: scaffold available; translation not started
```

Actively translated and allowed to follow clean scaffold artifacts:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: active
      refresh: artifact
      migrate_into: auto
      publish_release: true
      reason: actively translated
```

Published and frozen, while keeping the reviewed release assets available:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: published
      refresh: false
      migrate_into: false
      publish_release: true
      reason: published; do not rebuild from newer scaffold artifacts
```

Archived and fully frozen:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: archived
      refresh: false
      migrate_into: false
      publish_release: false
      reason: archived; keep historical branch and release assets unchanged
```

Published and archived versions must use `refresh: false`; the tooling rejects
frozen versions that could still be rebuilt from clean scaffold artifacts.
