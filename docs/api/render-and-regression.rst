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

DSW API Adapter
---------------

The adapter keeps server-generation differences out of workflow and rendering
services. Released document templates may be identified by coordinates or by a
UUID depending on the DSW runtime.

.. automodule:: dsw_document_template_tool.api
   :members: DSWApiClient, DSWAPIError, KnowledgeModelPackageReference
   :show-inheritance:

.. autoclass:: dsw_document_template_tool.models.DocumentTemplateReference
   :members:
   :no-index:
   :show-inheritance:

Render Project
--------------

.. automodule:: dsw_document_template_tool.render_project
   :members: ResolvedProject, render_project
   :show-inheritance:

Fixture Generation
------------------

.. automodule:: dsw_document_template_tool.fixture_coverage
   :members: BranchToken, GeneratedFixturePlan, plan_generated_fixture_cases
   :show-inheritance:

.. automodule:: dsw_document_template_tool.fixture_generator
   :members: GeneratedQuestionnaireEvents, generate_questionnaire_events
   :show-inheritance:

Runtime Evidence
----------------

.. automodule:: dsw_document_template_tool.regression_evidence
   :members: KnowledgeModelEvidence, RegressionEvidenceConfig, load_regression_evidence_config, validate_runtime_evidence, verify_knowledge_model_evidence
   :show-inheritance:

.. automodule:: dsw_document_template_tool.runtime_evidence
   :members: CoverageEvidence, VersionEvidence, RuntimeEvidence, collect_runtime_evidence, write_runtime_evidence, render_runtime_evidence
   :show-inheritance:

HTML Comparison
---------------

.. automodule:: dsw_document_template_tool.html_diff
   :members: normalize_html, build_unified_diff

Regression Internals
--------------------

.. automodule:: dsw_document_template_tool._regression.artifacts
   :members:
   :show-inheritance:

.. automodule:: dsw_document_template_tool._regression.parallel
   :members:
   :show-inheritance:

TDK Helpers
-----------

.. automodule:: dsw_document_template_tool.tdk
   :members: TemplateToolError, read_local_template_coordinates, stage_local_template_dir, verify_template_dir, put_template_dir, parse_template_coordinates
   :show-inheritance:

CLI Entry Points
----------------

.. automodule:: dsw_document_template_tool.cli.render_project
   :members: build_argument_parser, main

.. automodule:: dsw_document_template_tool.cli.render_regression
   :members: build_argument_parser, main
