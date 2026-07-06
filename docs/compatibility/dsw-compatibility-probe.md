# DSW Compatibility Probe

This page is the stable landing page for DSW compatibility probe reports.

When upstream publishes a template tag with an unsupported metamodel, CI runs
`make discover-upstream-compat` and may open a follow-up PR through
`make create-dsw-compat-pr`. That PR updates this page with the discovery
report, the optimistic runtime proposal, and the smoke-test checklist.

If this page only contains the placeholder text above, there is no active
compatibility probe checked into `master`.
