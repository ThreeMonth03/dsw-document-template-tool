Template Transform Reference
============================

Use this page for maintainer-facing transform entrypoints that expand upstream
DSW template source into translation-friendly workspaces and compact it back for
upload or comparison. Use the parser guide for the lower-level rewrite rules
behind these APIs.

Transform Facade
----------------

.. automodule:: dsw_document_template_tool.template_transform
   :members: expand_template_dir, compact_template_dir, explain_transform_workspace, snapshot_tree, TemplateTransformError
   :show-inheritance:

CLI Entry Point
---------------

.. automodule:: dsw_document_template_tool.cli.transform_template
   :members: build_argument_parser, main

Implementation Modules
----------------------

These modules are implementation details, but they are intentionally documented
for maintainers changing parser or rewrite behavior.

.. automodule:: dsw_document_template_tool._template_transform.models
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._template_transform.workspace
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._template_transform.scanner
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._template_transform.rewrite_rules
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._template_transform.profile
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._template_transform.science_europe
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._template_transform.science_europe_balanced_rules
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._template_transform.science_europe_unbalanced_rules
   :members:
   :show-inheritance:
