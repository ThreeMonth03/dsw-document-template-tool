# Branch Policy

This repository may combine translation work and public handoff in one GitHub
repository, but the responsibilities must stay separated by branch.

## Branch Layout

| Branch or asset | Purpose |
| --- | --- |
| `master` or the configured operations branch | Repository-level docs, `translation-config.yml`, and workflows. |
| `translation/v*` | Translator-facing Markdown workspaces and review PRs. |
| `sync/v*` or the configured publish branch prefix | Clean translated template source for handoff or manual import. |
| Release assets | Package zip, preview PDF, checksums, and release notes. |

Do not publish translator-facing workspaces as final template source. Use the
configured publish branch or release asset for reviewed handoff.

## Public Visibility

If this repository is public, translation branches and pull requests are public
too. That means draft translation wording, CI logs, preview artifacts, and
review discussions may be visible.

If draft translation work must stay private, keep `translation/v*` branches in a
private repository or private fork and publish only reviewed `sync/v*` branches
or release assets to the public repository.

## Version Policy

`translation-config.yml` controls which upstream versions are known and which
versions automation may refresh. A version can be scaffold-only without an
active translation branch.

Use `version_policy` to decide whether a version is active, maintenance-only,
or archived. Do not assume every upstream template tag needs an active
translation branch.
