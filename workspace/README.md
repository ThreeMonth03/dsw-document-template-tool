## Workspace

This directory is reserved for local/generated document-template workspaces.
Checked-in test inputs live under `fixtures/` instead:

- `fixtures/knowledge-models/`
  stores Knowledge Model bundles used by fixture projects and CI regression
- `fixtures/projects/`
  stores demo and regression project fixtures

Document template workspaces are intentionally not committed in this tooling
repository. The path `workspace/document-templates/` is ignored by Git and is
reserved for generated local workspaces or downstream translation repositories.

In this repo, clean upstream template workspaces are generated under `outputs/`
and uploaded as GitHub Actions artifacts. Downstream translation repos can keep
their own `workspace/document-templates/compact`, `expanded`, and `translation`
trees when translators need editable files.
