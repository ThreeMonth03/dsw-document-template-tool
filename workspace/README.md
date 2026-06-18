## Workspace

This directory keeps small, checked-in fixture assets used by local regression
runs and GitHub Actions:

- `knowledge-models/`
  stores KM bundles used by fixture projects and CI regression
- `projects/`
  stores portable project references and exported project events used for demo
  rendering

Document template workspaces are intentionally not committed in this tooling
repository. The path `workspace/document-templates/` is ignored by Git and is
reserved for generated local workspaces or downstream translation repositories.

In this repo, clean upstream template workspaces are generated under `outputs/`
and uploaded as GitHub Actions artifacts. Downstream translation repos can keep
their own `workspace/document-templates/compact`, `expanded`, and `translation`
trees when translators need editable files.
