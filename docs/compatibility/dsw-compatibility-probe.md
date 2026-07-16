# DSW Compatibility Probe

This page is the stable landing page for DSW compatibility probe reports.

When upstream publishes a template tag with an unsupported metamodel, CI runs
`make discover-upstream-compat` and may open a follow-up PR through
`make create-dsw-compat-pr`. That PR updates this page with the discovery
report, the optimistic runtime and pinned-KM proposal, and the validation
checklist.

If this page only contains the placeholder text above, there is no active
compatibility probe checked into `master`.

When CI updates an open probe PR, it uses that automation branch's current
runtime and evidence candidate. Maintainer experiments on the probe branch are
therefore retained across scheduled discovery runs.
