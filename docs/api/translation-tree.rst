Translation Tree Reference
==========================

Use this page for maintainer-facing translation-tree operations: export,
audit, exact-only migration, sync, XLIFF exchange, and translated-output
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
