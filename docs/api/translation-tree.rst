Translation Tree Reference
==========================

Use this page for maintainer-facing translation-tree operations: export,
audit, exact-source cross-version synchronization, sync, XLIFF exchange, and translated-output
structure checks. Use the parser guide before changing extraction, marker, or
Jinja safety internals.

Translation Tree Facade
-----------------------

.. automodule:: dsw_document_template_tool.translation_tree
   :members:
   :exclude-members: DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG, TREE_ROOT_NAME
   :show-inheritance:

CLI Entry Point
---------------

.. automodule:: dsw_document_template_tool.cli.translation_tree
   :members: build_argument_parser, main

Implementation Modules
----------------------

These modules define the editable Markdown format, tree manifest, exact-source
synchronization behavior, output polishing, XLIFF exchange, and structure audits.

.. automodule:: dsw_document_template_tool._translation_tree.models
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.document
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.extraction
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.source_quality_rules
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.apply
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.merge
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.manifest
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.outline
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.output_polish
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.structure_audit
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.tree_audit
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._translation_tree.xliff
   :members:
   :show-inheritance:
