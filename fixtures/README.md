# Render Fixtures

`empty-project.events.json` is a smoke fixture only. It proves the regression
pipeline can create and render a project, but it does not exercise the template's
deep `if`/`elif`/`else` and `for` branches.

For serious template upgrades, add exported DSW project event payloads here and
reference each one from `config/regression.preview.yml`. Prefer several focused
fixtures over one huge fixture, especially for list cardinalities (`0`, `1`,
`2`, `3+`) and mutually exclusive answer branches.
