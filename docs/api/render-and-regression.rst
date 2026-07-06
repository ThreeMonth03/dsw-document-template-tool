Render and Regression Reference
===============================

Use this page for maintainer-facing DSW rendering, fixture generation, HTML
comparison, and regression workflow entrypoints. Use the regression workflow
runbook for operational steps before running these APIs directly.

Regression Workflow Service
---------------------------

.. autoclass:: dsw_document_template_tool.workflow.DocumentTemplateWorkflowService
   :members: run
   :show-inheritance:

Render Project
--------------

.. automodule:: dsw_document_template_tool.render_project
   :members: ResolvedProject, render_project, build_argument_parser, main
   :show-inheritance:

Fixture Generation
------------------

.. automodule:: dsw_document_template_tool.fixture_generator
   :members: GeneratedQuestionnaireEvents, generate_questionnaire_events
   :show-inheritance:

HTML Comparison
---------------

.. automodule:: dsw_document_template_tool.html_diff
   :members: normalize_html, build_unified_diff

TDK Helpers
-----------

.. automodule:: dsw_document_template_tool.tdk
   :members: TemplateToolError, read_local_template_coordinates, stage_local_template_dir, verify_template_dir, put_template_dir, parse_template_coordinates
   :show-inheritance:

CLI Entry Points
----------------

.. automodule:: dsw_document_template_tool.cli.render_project
   :members: main

.. automodule:: dsw_document_template_tool.cli.render_regression
   :members: build_argument_parser, main
