Template Transform Reference
============================

Use this page for maintainer-facing transform entrypoints that expand upstream
DSW template source into translation-friendly workspaces and compact it back for
upload or comparison. Use the parser guide for the lower-level rewrite rules
behind these APIs.

Transform Facade
----------------

.. automodule:: dsw_document_template_tool.template_transform
   :members: expand_template_dir, compact_template_dir, snapshot_tree, TemplateTransformError
   :show-inheritance:

CLI Entry Point
---------------

.. automodule:: dsw_document_template_tool.cli.transform_template
   :members: build_argument_parser, main
