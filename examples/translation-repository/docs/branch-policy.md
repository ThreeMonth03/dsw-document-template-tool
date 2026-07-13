# Branch Policy

This repository combines translation work and reviewed release assets while
keeping repository-level operations separate from version workspaces.

## Branch Layout

| Branch or asset | Purpose |
| --- | --- |
| `master` or the configured operations branch | Repository-level docs, `translation-config.yml`, and workflows. |
| `sync/v*` | Translator-facing Markdown workspaces and review PRs. |
| Release assets | Default delivery path: package zip, preview PDF, checksums, and release notes. |

Do not treat translator-facing branch contents as an importable package. Use the
reviewed versioned release asset for manual import.

## Public Visibility

If this repository is public, translation branches and pull requests are public
too. That means draft translation wording, CI logs, preview artifacts, and
review discussions may be visible.

If draft translation work must stay private, keep `sync/v*` branches in a
private repository or private fork and publish only reviewed release assets.

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

Maintenance-only, requiring an operator-triggered refresh or migration:

```yaml
version_policy:
  overrides:
    vX.Y.Z:
      state: maintenance
      refresh: manual
      migrate_into: manual
      publish_release: true
      reason: maintenance changes require operator review
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

`state` must be one of `available`, `active`, `maintenance`, `published`, or
`archived`; spelling variants fail validation.

Policy precedence is `defaults`, matching `rules` in file order, and finally an
exact version `override`. A rule or override changes only the fields it contains,
so a reason-only override does not reset refresh, migration, or release behavior.
Use `artifact` and `auto` explicitly when enabling automation; do not use `true`
as shorthand.
